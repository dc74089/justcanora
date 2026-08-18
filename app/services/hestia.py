"""Thin client for driving the HestiaCP panel API on the student webserver.

This app runs in Docker on one host; the student webserver (HestiaCP) is a
separate machine. All management happens over the panel's HTTPS API on
:8083, POSTing `v-*` commands with a restricted access key. See hestia.md
for the operational background.

Everything is intentionally thin: one `_call` helper plus typed wrappers for
the handful of commands provisioning needs. A `dry_run` mode logs the intended
commands instead of sending them, so the whole flow is exercisable without
touching the live box.
"""
import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)


class HestiaError(Exception):
    """A `v-*` command returned a non-zero exit code (or the request failed)."""


class HestiaClient:
    def __init__(self, host=None, port=None, access_key=None, secret_key=None,
                 admin_user=None, admin_password=None, verify_ssl=None,
                 dry_run=None, timeout=30):
        self.host = host or settings.HESTIA_HOST
        self.port = port or settings.HESTIA_API_PORT
        self.access_key = access_key if access_key is not None else settings.HESTIA_ACCESS_KEY
        self.secret_key = secret_key if secret_key is not None else settings.HESTIA_SECRET_KEY
        self.admin_user = admin_user if admin_user is not None else settings.HESTIA_ADMIN_USER
        self.admin_password = admin_password if admin_password is not None else settings.HESTIA_ADMIN_PASSWORD
        self.verify_ssl = settings.HESTIA_VERIFY_SSL if verify_ssl is None else verify_ssl
        self.dry_run = settings.HESTIA_DRY_RUN if dry_run is None else dry_run
        self.timeout = timeout

        # The panel's self-signed cert makes urllib3 warn on every request when
        # verification is off (expected here); quiet it.
        if not self.verify_ssl:
            from urllib3.exceptions import InsecureRequestWarning
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    @property
    def base_url(self):
        return f"https://{self.host}:{self.port}/api/index.php"

    def _auth_params(self):
        # Prefer a restricted access key; fall back to admin login.
        if self.access_key and self.secret_key:
            return {"access_key": self.access_key, "secret_key": self.secret_key}
        if self.admin_user and self.admin_password:
            return {"user": self.admin_user, "password": self.admin_password}
        raise HestiaError(
            "No Hestia credentials configured (set HESTIA_ACCESS_KEY/HESTIA_SECRET_KEY "
            "or HESTIA_ADMIN_USER/HESTIA_ADMIN_PASSWORD)."
        )

    def _call(self, cmd, *args, returncode=True):
        """Run a single `v-*` command.

        With `returncode=True` the API returns just the numeric exit code; we
        treat "0" as success and raise otherwise. With `returncode=False` the
        command's own output is returned (for reads, pass "json" as the last
        arg to get JSON — Hestia has no separate `format` param).
        """
        params = {"cmd": cmd}
        for i, arg in enumerate(args, start=1):
            params[f"arg{i}"] = str(arg)
        if returncode:
            params["returncode"] = "yes"

        # Log (and, in dry-run, short-circuit) before attaching secrets so we
        # never write credentials to the log.
        printable = " ".join(str(a) for a in args)
        if self.dry_run:
            log.info("[hestia dry-run] %s %s", cmd, printable)
            return "0" if returncode else ""
        log.info("[hestia] %s %s", cmd, printable)

        params.update(self._auth_params())
        try:
            resp = requests.post(self.base_url, data=params,
                                 verify=self.verify_ssl, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise HestiaError(f"{cmd} request failed: {e}") from e

        body = resp.text.strip()
        if returncode:
            if body != "0":
                raise HestiaError(f"{cmd} {printable} -> exit code {body!r}")
            return body
        return body

    # -- reads -------------------------------------------------------------

    def raw(self, cmd, *args):
        """Low-level data-mode call returning the untouched response text.
        Useful for debugging what the panel actually sends back."""
        return self._call(cmd, *args, returncode=False)

    def _call_json(self, cmd, *args):
        import json
        raw = self._call(cmd, *args, "json", returncode=False)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise HestiaError(
                f"{cmd} did not return JSON (access key may lack permission for "
                f"{cmd}, or the API is misconfigured). Response was: {raw[:300]!r}"
            )

    def list_users(self):
        """Return the panel's user list as a dict keyed by username."""
        return self._call_json("v-list-users")

    def user_exists(self, username):
        return username in self.list_users()

    def list_web_domains(self, username):
        """Return a user's web domains as a dict keyed by domain."""
        return self._call_json("v-list-web-domains", username)

    def web_domain_exists(self, username, domain):
        return domain in self.list_web_domains(username)

    # -- account lifecycle -------------------------------------------------

    def add_user(self, username, password, email, first, last, package=None):
        package = package or settings.HESTIA_STUDENT_PACKAGE
        return self._call("v-add-user", username, password, email, package, first, last)

    def add_web_domain(self, username, domain):
        return self._call("v-add-web-domain", username, domain)

    def set_shell(self, username, shell=None):
        """Set a user's login shell (default jailbash) so chrooted SFTP works.
        New Hestia users get `nologin`, which blocks SFTP. Idempotent — safe to
        re-run on already-correct accounts."""
        shell = shell or settings.HESTIA_SFTP_SHELL
        return self._call("v-change-user-shell", username, shell)

    # -- SSL ---------------------------------------------------------------

    def install_ssl_wildcard(self, username, domain):
        """Install the shared wildcard cert on a subdomain.

        Delegates to a box-side wrapper (`v-add-web-domain-ssl-wildcard`, see
        the runbook) that renames the acme.sh wildcard files to the per-domain
        names Hestia requires (`<domain>.crt`/`.key`) and picks add-vs-update
        automatically. Plain `v-add-web-domain-ssl` can't be pointed straight
        at the acme.sh dir — it looks for `<domain>.crt` and fails (exit 3).
        """
        return self._call("v-add-web-domain-ssl-wildcard", username, domain, settings.HESTIA_BASE_DOMAIN)

    def install_ssl_letsencrypt(self, username, domain):
        """Issue a per-domain Let's Encrypt cert (shark tank real domains).

        Requires the domain's DNS to already point at the webserver, so callers
        should treat this as a retryable step separate from account creation.
        """
        return self._call("v-add-letsencrypt-domain", username, domain)

    # -- basic auth (personal sites only) ----------------------------------

    def add_httpauth(self, username, domain, auth_user=None, auth_password=None):
        auth_user = auth_user or settings.HESTIA_BASIC_AUTH_USER
        auth_password = auth_password or settings.HESTIA_BASIC_AUTH_PASSWORD
        return self._call("v-add-web-domain-httpauth", username, domain, auth_user, auth_password)

    def delete_httpauth(self, username, domain, auth_user=None):
        auth_user = auth_user or settings.HESTIA_BASIC_AUTH_USER
        return self._call("v-delete-web-domain-httpauth", username, domain, auth_user)
