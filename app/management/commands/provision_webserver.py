"""Provision student hosting on the HestiaCP webserver.

Personal sites come from the CS1 roster; shark-tank projects come from
SharkProject rows (managed in the admin). By default this runs in dry-run
mode (log the intended v-* commands, send nothing) unless HESTIA_DRY_RUN=0
is set in the environment; --dry-run forces dry-run on regardless.

Examples:
    manage.py provision_webserver --dry-run            # preview personal + shark
    manage.py provision_webserver --personal --force   # (re)push all personal sites
    manage.py provision_webserver --shark              # create shark accounts + domains
    manage.py provision_webserver --shark-ssl          # issue shark LE certs (needs live DNS)
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from app.models import SharkProject
from app.services.hestia import HestiaClient
from app.tasks import webserver_creds as ws


class Command(BaseCommand):
    help = "Provision personal student sites and shark-tank projects on the HestiaCP webserver."

    def add_arguments(self, parser):
        parser.add_argument("--year", default=settings.CURRENT_ACADEMIC_YEAR)
        parser.add_argument("--semester", type=int, default=settings.CURRENT_SEMESTER)
        parser.add_argument("--dry-run", action="store_true",
                            help="Log intended v-* commands without sending them.")
        parser.add_argument("--force", action="store_true",
                            help="Re-provision rows already marked provisioned.")
        parser.add_argument("--personal", action="store_true",
                            help="Provision personal student sites.")
        parser.add_argument("--shark", action="store_true",
                            help="Provision shark-tank accounts + domains (no SSL).")
        parser.add_argument("--shark-ssl", action="store_true",
                            help="Issue shark-tank Let's Encrypt certs (requires live DNS).")

    def handle(self, *args, **opts):
        year, semester, force = opts["year"], opts["semester"], opts["force"]

        # If no target flag is given, do personal + shark account provisioning
        # (but not the DNS-dependent shark SSL step).
        selected = opts["personal"] or opts["shark"] or opts["shark_ssl"]
        do_personal = opts["personal"] or not selected
        do_shark = opts["shark"] or not selected
        do_shark_ssl = opts["shark_ssl"]

        client = HestiaClient(dry_run=True if opts["dry_run"] else None)
        self.stdout.write(
            f"Target: {client.host}:{client.port} | "
            f"{'DRY-RUN (no commands sent)' if client.dry_run else self.style.WARNING('LIVE')} | "
            f"{year} S{semester}"
        )

        if do_personal:
            ws.generate_creds(year=year, semester=semester)  # ensure local rows exist
            creds = ws.personal_creds_for(year=year, semester=semester)
            if not force:
                creds = creds.filter(provisioned_at__isnull=True)
            self._run("personal", creds, lambda c: ws.provision_personal(c, client=client))

        if do_shark:
            projects = SharkProject.objects.filter(year=year, semester=semester)
            if not force:
                projects = projects.filter(provisioned_at__isnull=True)
            self._run("shark", projects, lambda p: ws.provision_shark(p, client=client))

        if do_shark_ssl:
            projects = SharkProject.objects.filter(year=year, semester=semester)
            if not force:
                projects = projects.filter(ssl_installed=False)
            self._run("shark-ssl", projects, lambda p: ws.provision_shark_ssl(p, client=client))

    def _run(self, label, items, action):
        items = list(items)
        self.stdout.write(f"\n[{label}] {len(items)} to process")
        ok = failed = 0
        for item in items:
            try:
                action(item)
                ok += 1
                self.stdout.write(self.style.SUCCESS(f"  ok    {item}"))
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  FAIL  {item}: {e}"))
        summary = f"[{label}] done: {ok} ok, {failed} failed"
        self.stdout.write(self.style.SUCCESS(summary) if not failed else self.style.WARNING(summary))
