import hmac

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render

from app.models import WebserverCredential, SharkProject


def _connection_context():
    """SFTP/basic-auth details shared by the student and staff templates."""
    return {
        "sftp_host": settings.HESTIA_SFTP_HOST,
        "sftp_port": settings.HESTIA_SFTP_PORT,
        "basic_auth_user": settings.HESTIA_BASIC_AUTH_USER,
        "basic_auth_password": settings.HESTIA_BASIC_AUTH_PASSWORD,
    }


def instructions(request):
    student = request.user.student
    creds = WebserverCredential.objects.filter(student=student).first()

    ctx = {
        "creds": creds,
        "shark_projects": student.shark_projects.all(),
        **_connection_context(),
    }
    return render(request, "app/webserver/instructions.html", ctx)


def _roster_token(request):
    """Bearer token from the Authorization header, falling back to ?token=."""
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):]
    return request.GET.get("token", "")


def ssl_roster(request):
    """Plain-text roster of provisioned personal accounts (one `username
    subdomain` per line) for the webserver's acme.sh --reloadcmd to re-push
    the shared *.lhpscs.com wildcard cert. Shark projects are excluded: they
    carry their own per-domain certs, renewed by Hestia's native cron.

    Token-authenticated (the box is not a logged-in user). If the token is
    unset the endpoint is effectively disabled.
    """
    expected = settings.HESTIA_ROSTER_TOKEN
    if not expected or not hmac.compare_digest(_roster_token(request), expected):
        return HttpResponseForbidden("forbidden\n", content_type="text/plain")

    creds = (WebserverCredential.objects
             .filter(provisioned_at__isnull=False, username__isnull=False)
             .order_by("username"))
    body = "".join(f"{c.username} {c.subdomain}\n" for c in creds)
    return HttpResponse(body, content_type="text/plain")


@staff_member_required
def all_table(request):
    ctx = {
        "creds": WebserverCredential.objects.all().order_by('student__lname', 'username'),
        "shark_projects": SharkProject.objects.all().order_by('period', 'group_number'),
        **_connection_context(),
    }
    return render(request, "app/webserver/all_table.html", ctx)
