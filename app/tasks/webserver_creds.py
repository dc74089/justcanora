import logging

from django.conf import settings
from django.utils import timezone

from app.models import Course, WebserverCredential, SharkProject, Student
from app.services.hestia import HestiaClient, HestiaError

log = logging.getLogger(__name__)


# -- local row creation (no webserver contact) ----------------------------

def generate_creds(year=settings.CURRENT_ACADEMIC_YEAR, semester=settings.CURRENT_SEMESTER):
    s: Student
    for c in Course.objects.filter(year=year, semester=semester, type="CS1"):
        for s in c.students.all():
            generate_cred_for_student(s.id)


def generate_cred_for_student(student_id):
    """Create the local personal-hosting row for a student (email prefix ==
    Hestia login). Pushing the account to the webserver is done separately by
    provision_personal()."""
    student = Student.objects.get(id=student_id)

    if not student.has_web_credential():
        if student.email:
            wc = WebserverCredential(
                student=student,
                username=student.email.split("@")[0],
                password=WebserverCredential.gen_password(),
            )
            wc.save()
        else:
            print("No email")


def personal_creds_for(year=settings.CURRENT_ACADEMIC_YEAR, semester=settings.CURRENT_SEMESTER):
    """The personal credentials belonging to students on the CS1 roster."""
    student_ids = Course.objects.filter(
        year=year, semester=semester, type="CS1"
    ).values_list("students__id", flat=True)
    return WebserverCredential.objects.filter(student__id__in=student_ids)


def accounts_with_username():
    """Every existing account that has a Hestia login (personal + shark),
    regardless of provisioned status — used to retroactively enforce the SFTP
    shell on accounts already created on the box."""
    personal = WebserverCredential.objects.exclude(username__isnull=True).exclude(username="")
    shark = SharkProject.objects.exclude(username__isnull=True).exclude(username="")
    return list(personal) + list(shark)


def enforce_shell(account, client=None):
    """Set the SFTP login shell (jailbash) on one existing account."""
    client = client or HestiaClient()
    client.set_shell(account.username)
    return account


# -- provisioning (pushes to the webserver via the Hestia API) -------------

def provision_personal(cred: WebserverCredential, client=None, install_ssl=True):
    """Create a student's personal account on the webserver:
    user -> web domain -> wildcard SSL -> shared mscs/mscs basic auth.

    Idempotent on the pieces most likely to survive a partial run (user, web
    domain). Stamps provisioned_at/ssl_installed on success.
    """
    if not cred.username or not cred.password:
        raise ValueError(f"{cred} is missing a username/password")
    if not (cred.student and cred.student.email):
        raise ValueError(f"{cred} has no student email")

    client = client or HestiaClient()
    student = cred.student
    domain = cred.subdomain

    if not client.user_exists(cred.username):
        client.add_user(cred.username, cred.password, student.email, student.fname, student.lname)
    client.set_shell(cred.username)  # jailbash: enable chrooted SFTP (idempotent)
    if not client.web_domain_exists(cred.username, domain):
        client.add_web_domain(cred.username, domain)

    # Shared basic-auth prompt on every personal site. Benign if already set,
    # so don't let it fail an otherwise-good provision.
    try:
        client.add_httpauth(cred.username, domain)
    except HestiaError as e:
        log.warning("basic auth for %s may already be set: %s", domain, e)

    if install_ssl:
        client.install_ssl_wildcard(cred.username, domain)
        cred.ssl_installed = True

    cred.provisioned_at = timezone.now()
    if not client.dry_run:
        cred.save(update_fields=["provisioned_at", "ssl_installed"])
    return cred


def _prepare_shark(project: SharkProject, persist=True):
    """Ensure a shark project has a group login + password before provisioning."""
    dirty = []
    if not project.username:
        project.username = f"shark{project.period}{project.group_number}"
        dirty.append("username")
    if not project.password:
        project.password = SharkProject.gen_password()
        dirty.append("password")
    if dirty and persist:
        project.save(update_fields=dirty)


def provision_shark(project: SharkProject, client=None):
    """Create a shark-tank group account on the webserver: shared group user
    -> web domain (its own real domain). No basic auth. SSL is a separate,
    retryable step (provision_shark_ssl) because it depends on live DNS.
    """
    if not project.domain:
        raise ValueError(f"{project} has no domain set")

    client = client or HestiaClient()
    _prepare_shark(project, persist=not client.dry_run)

    # Groups have no single student, so synthesize the account contact fields.
    email = f"{project.username}@{settings.HESTIA_BASE_DOMAIN}"
    if not client.user_exists(project.username):
        client.add_user(project.username, project.password, email, "Shark", project.label())
    client.set_shell(project.username)  # jailbash: enable chrooted SFTP (idempotent)
    if not client.web_domain_exists(project.username, project.domain):
        client.add_web_domain(project.username, project.domain)

    project.provisioned_at = timezone.now()
    if not client.dry_run:
        project.save(update_fields=["provisioned_at"])
    return project


def provision_shark_ssl(project: SharkProject, client=None):
    """Issue the per-domain Let's Encrypt cert for a shark project.

    Retryable and separate from provision_shark(): it only succeeds once the
    domain's DNS points at the webserver, which is a manual step per project.
    """
    if not (project.username and project.domain):
        raise ValueError(f"{project} is not ready for SSL (missing username/domain)")

    client = client or HestiaClient()
    client.install_ssl_letsencrypt(project.username, project.domain)
    project.ssl_installed = True
    if not client.dry_run:
        project.save(update_fields=["ssl_installed"])
    return project
