# Student Webserver — Sysadmin Runbook

Operational guide for managing student hosting (`lhpscs.com`) from the
Django app (justcanora). Companion to `hestia.md`, which covers the
background and box-side design decisions; this file is the "what do I
actually run" checklist.

## The setup in one picture

- **App** (justcanora) runs in Docker on one host. It is the **source of
  truth** for who has hosting.
- **Webserver** is a separate HestiaCP box. The app drives it over the
  panel API on `:8083` (HTTPS) using `v-*` commands.
- Two kinds of hosting:
  - **Personal sites** — one per CS1 student, at `<username>.lhpscs.com`,
    behind a shared `mscs`/`mscs` basic-auth prompt. Covered by one shared
    `*.lhpscs.com` wildcard cert.
  - **Shark-tank projects** — one per group (2–4 students), each on its own
    **real registered domain**, no basic auth, each with its own Let's
    Encrypt cert.

Code map: `app/services/hestia.py` (API client), `app/tasks/webserver_creds.py`
(provisioning logic), `app/management/commands/` (`provision_webserver`,
`hestia_check`), models `WebserverCredential` + `SharkProject`.

## Safety model — read this first

The app **cannot** send real commands to the box unless you explicitly turn
off the guard rail:

- `HESTIA_DRY_RUN=1` is the **default**. In dry-run, every command is logged
  but nothing is sent to the box and nothing is stamped in the local DB.
- To actually provision, set `HESTIA_DRY_RUN=0` in the environment for that
  run.
- `--dry-run` on `provision_webserver` forces dry-run on regardless of the
  env, for safe previews.
- `hestia_check` is always read-only.

Rule of thumb: **preview with `--dry-run`, then re-run with `HESTIA_DRY_RUN=0`.**

## Environment variables

Set these in the app's environment (Docker env / secrets).

| Variable | Default | Purpose |
|---|---|---|
| `HESTIA_HOST` | `167.71.163.179` | Webserver / panel host |
| `HESTIA_API_PORT` | `8083` | Panel API port |
| `HESTIA_ACCESS_KEY` / `HESTIA_SECRET_KEY` | — | Preferred API auth (restricted key) |
| `HESTIA_ADMIN_USER` / `HESTIA_ADMIN_PASSWORD` | — | Fallback API auth (admin login) |
| `HESTIA_VERIFY_SSL` | `0` | Verify the panel's TLS cert (`1` once trusted) |
| `HESTIA_BASE_DOMAIN` | `lhpscs.com` | Base domain for personal subdomains |
| `HESTIA_SFTP_HOST` | = `HESTIA_HOST` | Host shown in students' `sftp.json` |
| `HESTIA_SFTP_PORT` | `22` | SFTP port shown in `sftp.json` |
| `HESTIA_STUDENT_PACKAGE` | `student_package` | Hestia package for new users |
| `HESTIA_CERT_DIR` | `/root/.acme.sh/lhpscs.com_ecc/` | Wildcard cert dir on the box |
| `HESTIA_BASIC_AUTH_USER` / `HESTIA_BASIC_AUTH_PASSWORD` | `mscs` / `mscs` | Shared basic-auth on personal sites |
| `HESTIA_DRY_RUN` | `1` | Guard rail — `0` to send real commands |
| `HESTIA_ROSTER_TOKEN` | — (empty = off) | Bearer token for the SSL roster endpoint |

## One-time setup

### On the webserver box
1. Create the `student_package` (disk quota ~250–500 MB, max web domains = 1,
   mail/DNS/DB = 0).
2. Allow subdomain creation under the base domain:
   `v-add-web-domain-allow-users admin lhpscs.com`
3. Issue the wildcard cert with acme.sh (DNS-01) — see `hestia.md` Path A/B.
   The result lives in `HESTIA_CERT_DIR` (`/root/.acme.sh/lhpscs.com_ecc/`).
4. **Install the wildcard-SSL wrapper.** Hestia's `v-add-web-domain-ssl` wants
   cert files named `<domain>.crt`/`.key`, but acme.sh stores
   `fullchain.cer`/`lhpscs.com.key` — pointing it at the acme dir fails with
   exit 3. This wrapper stages domain-named files and installs (add or update):
   ```bash
   cat > /usr/local/hestia/bin/v-add-web-domain-ssl-wildcard <<'EOF'
   #!/bin/bash
   # info: install the shared wildcard acme.sh cert onto a Hestia web domain
   # options: USER DOMAIN [BASE_DOMAIN] [RESTART]
   user="$1"; domain="$2"; base_domain="${3:-lhpscs.com}"; restart="$4"
   source /etc/hestiacp/hestia.conf
   source $HESTIA/func/main.sh
   source $HESTIA/func/domain.sh
   check_args '2' "$#" 'USER DOMAIN [BASE_DOMAIN] [RESTART]'
   is_object_valid 'user' 'USER' "$user"
   is_object_valid 'web' 'DOMAIN' "$domain"
   acme_dir="/root/.acme.sh/${base_domain}_ecc"
   [ -d "$acme_dir" ] || acme_dir="/root/.acme.sh/${base_domain}"
   src_crt="$acme_dir/fullchain.cer"; src_key="$acme_dir/${base_domain}.key"
   [ -e "$src_crt" ] || check_result "$E_NOTEXIST" "$src_crt not found"
   [ -e "$src_key" ] || check_result "$E_NOTEXIST" "$src_key not found"
   stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
   cp -f "$src_crt" "$stage/$domain.crt"; cp -f "$src_key" "$stage/$domain.key"
   chmod 600 "$stage/$domain".*
   if [ "$(get_object_value 'web' 'DOMAIN' "$domain" '$SSL')" = "yes" ]; then
       $BIN/v-update-web-domain-ssl "$user" "$domain" "$stage" "$restart"
   else
       $BIN/v-add-web-domain-ssl "$user" "$domain" "$stage" "same" "$restart"
   fi
   exit $?
   EOF
   chown root:root /usr/local/hestia/bin/v-add-web-domain-ssl-wildcard
   chmod 755 /usr/local/hestia/bin/v-add-web-domain-ssl-wildcard
   ```
5. **Create the API permission profile + key.** A key's `PERMISSIONS` is a list
   of *profile* names (files in `/usr/local/hestia/data/api/`), each holding a
   `COMMANDS=` list; a command not covered 401s. Create a profile with exactly
   what the app calls, then a key bound to it:
   ```bash
   cat > /usr/local/hestia/data/api/csclass <<'EOF'
   ROLE='admin'
   COMMANDS='v-make-tmp-file,v-list-users,v-list-web-domains,v-add-user,v-add-web-domain,v-add-web-domain-ssl-wildcard,v-add-letsencrypt-domain,v-add-web-domain-httpauth,v-delete-web-domain-httpauth,v-change-user-password,v-suspend-user,v-unsuspend-user,v-delete-user'
   EOF
   chown root:root /usr/local/hestia/data/api/csclass
   chmod 640 /usr/local/hestia/data/api/csclass
   v-add-access-key 'admin' 'csclass' 'cs-class-app' json   # returns ACCESS_KEY_ID + SECRET
   ```
   Put the returned key into the app's `HESTIA_ACCESS_KEY`/`HESTIA_SECRET_KEY`.
   Open/firewall `:8083` so only the app host's IP can reach it, and add that IP
   to the key's allowed IPs if using Hestia's `API_ALLOWED_IP`.
   To change scope later, just edit `COMMANDS=` in the profile (no key rotation).
6. Install `hestia-push-wildcard-cert.sh` as the acme.sh `--reloadcmd`
   (script in `hestia.md` → Renewal automation; it loops the roster and calls
   the wrapper above).

### In the app
1. Set the `HESTIA_*` env vars above (at minimum the host + access key +
   `HESTIA_ROSTER_TOKEN`).
2. Verify connectivity (read-only, safe):
   ```bash
   manage.py hestia_check
   # OK — connected, N user(s) on the box.
   ```
   Troubleshoot with the hints it prints if it fails (host/port, `:8083`
   firewall, credentials).
3. Confirm the SFTP details baked into `sftp.json` (port `22`, remote path
   `/web/<domain>/public_html`) match the live box; override
   `HESTIA_SFTP_PORT` if needed.

## Start-of-semester: provision personal sites

1. Make sure the CS1 courses/rosters for the current year+semester are
   imported (personal creds are generated from the CS1 roster).
2. Preview:
   ```bash
   manage.py provision_webserver --dry-run --personal
   ```
   Check the `v-add-user → v-add-web-domain → httpauth → SSL` sequences.
3. Go live:
   ```bash
   HESTIA_DRY_RUN=0 manage.py provision_webserver --personal
   ```
   Already-provisioned students are skipped automatically. One failure is
   reported and skipped without aborting the batch.
4. Confirm status in the staff table: **`/webserver/all_creds/`** (each row
   shows provisioned / SSL badges + the student's `sftp.json`).

## Add a mid-year student

1. Add them to the CS1 course roster (same as everyone else).
2. Provision — it only touches students who don't yet have an account:
   ```bash
   HESTIA_DRY_RUN=0 manage.py provision_webserver --personal
   ```
   They get the wildcard cert immediately at provision, and appear in the
   SSL roster so future renewals keep re-pushing to them.

## Shark-tank projects

Shark projects are defined in the **Django admin**, then provisioned.

1. In admin → **Shark projects** → add one per group:
   - `name`, `domain` (the real registered domain), `period`, `group_number`
     (identity is `period-group`, e.g. `1-4`), `year`/`semester`.
   - Add the student **members** (they'll see the shared creds on their
     instructions page).
   - Leave `username`/`password` blank — provisioning fills them
     (`shark<period><group>`, e.g. `shark14`, + a generated password).
2. **Point each domain's DNS at the VPS** (registrar) — required before SSL.
3. Preview + create the accounts and domains (no SSL yet):
   ```bash
   manage.py provision_webserver --dry-run --shark
   HESTIA_DRY_RUN=0 manage.py provision_webserver --shark
   ```
4. Once DNS resolves, issue the per-domain Let's Encrypt certs (retryable —
   safe to re-run until DNS has propagated for all):
   ```bash
   HESTIA_DRY_RUN=0 manage.py provision_webserver --shark-ssl
   ```
5. Members see their group's domain, login, and `sftp.json` on their own
   **/webserver/instructions/** page; you see all of it (with status badges)
   in **/webserver/all_creds/**.

> Running `provision_webserver` with no target flag does personal **and**
> shark account provisioning (but not the DNS-dependent `--shark-ssl` step).

## Handing out credentials

- Students self-serve: the instructions page (**/webserver/instructions/**)
  renders their exact `sftp.json` (personal + any shark projects) and site
  links. Linked from their dashboard "Important Links" card.
- Staff overview / manual handout: **/webserver/all_creds/** — reveals each
  password and `sftp.json`, with provisioned/SSL status.

## SSL & renewal

- **Personal (wildcard):** installed at provision time. Renewal is handled on
  the box by acme.sh, whose `--reloadcmd` pulls the current account list from
  the app's roster endpoint and re-pushes the refreshed cert. Nothing to do
  per-renewal.
  - Roster endpoint: `GET /webserver/ssl_roster/` — bearer-token auth
    (`HESTIA_ROSTER_TOKEN`), returns provisioned personal accounts only, one
    `username subdomain` per line. Empty token = endpoint disabled (403).
  - Quick manual check:
    ```bash
    curl -fsS -H "Authorization: Bearer $HESTIA_ROSTER_TOKEN" \
      https://tr.canora.us/webserver/ssl_roster/
    ```
- **Shark (per-domain):** issued via `--shark-ssl`; Hestia's native LE cron
  renews these. They are intentionally **not** in the wildcard roster.

## Not yet automated (do these on the box for now)

Provisioning is built; the rest of the account lifecycle is not yet wired
into the app. Until it is, use the panel or `v-*` CLI directly:

- **Reset a password:** `v-change-user-password <username> '<newpass>'` (then
  update the stored password in the app's DB / admin so `sftp.json` matches).
- **Suspend / unsuspend:** `v-suspend-user` / `v-unsuspend-user`.
- **Delete an account:** `v-delete-user <username>` (and delete the row in the
  app).

If any of these become routine, they're natural next additions to
`HestiaClient` + `provision_webserver`.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `hestia_check` → "Auth: NONE configured" | Set `HESTIA_ACCESS_KEY`/`HESTIA_SECRET_KEY` (or admin login) |
| `hestia_check` → request failed / timeout | `:8083` not reachable — check firewall/whitelist for the app host, and `HESTIA_HOST`/`HESTIA_API_PORT` |
| Auth fails with a valid-looking key | Param names vary by Hestia version; the client uses `access_key`/`secret_key`. Confirm against your version |
| Provisioning "did nothing" | Rows already provisioned (skipped). Use `--force` to re-run, or check you set `HESTIA_DRY_RUN=0` |
| Preview looks right but box unchanged | You were in dry-run — set `HESTIA_DRY_RUN=0` |
| `--shark-ssl` fails | DNS for that domain isn't pointing at the VPS yet; re-run once it resolves |
| Student `sftp.json` won't connect | Confirm `HESTIA_SFTP_PORT` and the `/web/<domain>/public_html` chroot path against the live box |
| Roster endpoint returns `forbidden` | `HESTIA_ROSTER_TOKEN` unset or mismatched between app and reloadcmd |

## Quick reference

```bash
# Read-only connectivity / credentials test
manage.py hestia_check [--users] [--user <username>]

# Preview everything (sends nothing)
manage.py provision_webserver --dry-run

# Provision (LIVE — note HESTIA_DRY_RUN=0)
HESTIA_DRY_RUN=0 manage.py provision_webserver --personal
HESTIA_DRY_RUN=0 manage.py provision_webserver --shark
HESTIA_DRY_RUN=0 manage.py provision_webserver --shark-ssl
HESTIA_DRY_RUN=0 manage.py provision_webserver --force        # re-push existing

# Scope to a specific term
manage.py provision_webserver --year 26/27 --semester 1 ...
```

Pages: `/webserver/instructions/` (student) · `/webserver/all_creds/` (staff)
· `/webserver/ssl_roster/` (token). Shark projects: Django admin → Shark
projects.
