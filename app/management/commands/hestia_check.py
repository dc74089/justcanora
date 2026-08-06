"""Read-only connectivity check against the HestiaCP panel API.

Runs `v-list-users` (and optionally `v-list-web-domains <user>`) to validate
network reachability, the firewall opening on :8083, and API credentials
without creating or changing anything. Always makes a real request, ignoring
HESTIA_DRY_RUN, since a dry-run connectivity check would be meaningless.

    manage.py hestia_check
    manage.py hestia_check --users          # also print each username
    manage.py hestia_check --user jdoe       # also list that user's web domains
"""
from django.core.management.base import BaseCommand

from app.services.hestia import HestiaClient, HestiaError


class Command(BaseCommand):
    help = "Read-only connectivity/credentials check against the HestiaCP panel API."

    def add_arguments(self, parser):
        parser.add_argument("--users", action="store_true",
                            help="Print every username returned, not just the count.")
        parser.add_argument("--user", help="Also list this user's web domains.")

    def handle(self, *args, **opts):
        # Read-only, so force a real request regardless of HESTIA_DRY_RUN.
        client = HestiaClient(dry_run=False)

        if client.access_key and client.secret_key:
            auth = "access key"
        elif client.admin_user and client.admin_password:
            auth = f"admin login ({client.admin_user})"
        else:
            auth = self.style.ERROR("NONE configured")
        self.stdout.write(f"Target: {client.host}:{client.port}")
        self.stdout.write(f"Auth:   {auth}")
        self.stdout.write(f"Verify SSL: {client.verify_ssl}")

        try:
            users = client.list_users()
        except HestiaError as e:
            raise self._fail(f"Could not reach the panel API: {e}")

        self.stdout.write(self.style.SUCCESS(f"OK — connected, {len(users)} user(s) on the box."))
        if opts["users"]:
            for name in sorted(users):
                self.stdout.write(f"  {name}")

        if opts["user"]:
            target = opts["user"]
            try:
                domains = client.list_web_domains(target)
            except HestiaError as e:
                raise self._fail(f"Could not list web domains for {target!r}: {e}")
            self.stdout.write(f"\n{target}: {len(domains)} web domain(s)")
            for domain in sorted(domains):
                self.stdout.write(f"  {domain}")

    def _fail(self, message):
        from django.core.management.base import CommandError
        self.stdout.write(self.style.ERROR(message))
        self.stdout.write(
            "Check: HESTIA_HOST/HESTIA_API_PORT, that :8083 is reachable from this host "
            "(firewall/whitelist), and HESTIA_ACCESS_KEY/HESTIA_SECRET_KEY (or admin login)."
        )
        return CommandError("hestia_check failed")
