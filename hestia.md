# HestiaCP Student Hosting Setup — lhpscs.com

Reference notes for a self-hosted HestiaCP environment providing ~100 middle
school students (MS CS 1, web design class) with FTP/SFTP access to publish
static/dynamic web content. Account provisioning, per-account SSL install,
and the renewal roster are now integrated into the Django app (justcanora)
over the HestiaCP panel API; what remains is box-side setup and go-live
(wildcard cert issuance, API key + firewall, DNS).

## Environment

- **Panel:** HestiaCP (self-hosted, FOSS), single VPS
- **Base domain:** `lhpscs.com`
- **DNS host:** Namecheap
- **Scale:** ~100 student accounts
- **Access model:** FTP/SFTP only — no shell/SSH terminal access needed or
  wanted for students
- **Account model:** one Hestia "user" = one student, each with their own
  subdomain (`<username>.lhpscs.com`) as their default web domain and doc
  root. This gives each student an isolated chrooted SFTP login (Hestia's
  default behavior — no shell, jailed to their own home dir) with zero
  cross-visibility between students.

## Account provisioning

Driven from the Django app over the HestiaCP panel API on :8083 — see
`app/services/hestia.py` (thin `v-*` client) and the `provision_webserver`
management command. The app is the source of truth; there is no hand-run
CLI loop.

```bash
# one-time on the box: a "student" package to keep accounts minimal
# (disk quota ~250-500MB, max web domains = 1, max mail/DNS/DB = 0)

# from the app (dry-run logs the intended v-* calls and sends nothing):
manage.py provision_webserver --dry-run
manage.py provision_webserver --personal   # per CS1-roster student:
                                            #   v-add-user … student_package <first> <last>
                                            #   v-add-web-domain <username>.lhpscs.com
                                            #   v-add-web-domain-httpauth (shared mscs/mscs)
                                            #   wildcard SSL install
manage.py provision_webserver --shark       # shark-tank groups: own real domain, no basic auth
manage.py provision_webserver --shark-ssl   # per-domain Let's Encrypt (needs live DNS first)
```

Safety: `HESTIA_DRY_RUN=1` by default — must set `=0` to send real commands.
`manage.py hestia_check` is a read-only connectivity/credentials test
(`v-list-users`). Still to decide: exact package limits.

## Issues hit so far (resolved)

**Subdomain ownership error** — Hestia blocks a user from creating a
subdomain under a domain they don't own, as an anti-hijacking guard:
```bash
# run as whoever owns the base domain (e.g. admin)
v-add-web-domain-allow-users admin lhpscs.com
```
One-time fix; after this any user can create `<theirname>.lhpscs.com`.

**Hiding internal IPs from the dashboard** — Hestia's IP list only shows
registered IPs, not everything on the box:
```bash
v-list-sys-ips                  # confirm exact IP strings
v-delete-sys-ip <internal-ip>   # remove from Hestia's registry
```
Constraints: won't delete an IP that's the first IP on its interface, or
one actively assigned to a web domain (reassign the domain first via
`v-change-web-domain-ip` if needed). These don't silently reappear —
`v-update-sys-ip` (the rescan/re-register command) is not part of Hestia's
default cron, so deletions stick unless someone manually reruns it.

## NEXT TASK: SSL / Let's Encrypt

**Not started yet.** Key findings from planning, to pick up from here:

### The core problem
Giving each of 100 student subdomains its own individually-requested
Let's Encrypt cert (via Hestia's native panel button) will hit Let's
Encrypt's rate limit: **50 new certificates per registered domain
(lhpscs.com, regardless of subdomain) per 7 days**, refilling slowly
(~1 every 202 minutes). First ~50 students provision fine, rest fail
until the following week. Also: **HestiaCP's built-in Let's Encrypt
integration only supports HTTP-01** — no wildcard option in the panel UI.

### The fix: one wildcard certificate for everyone
A single `*.lhpscs.com` + `lhpscs.com` certificate covers every student
subdomain and only counts as **one** issuance against the rate limit
(instead of 100). Requires DNS-01 challenge via an external ACME client
(`acme.sh`), then manually installing the resulting cert into each
student's Hestia web domain.

### First-time acme.sh setup (both paths)

```bash
# 1. Install (sets up its own daily renew cron)
curl https://get.acme.sh | sh -s email=admin@lhpscs.com

# 2. Use Let's Encrypt (acme.sh now defaults to ZeroSSL)
/root/.acme.sh/acme.sh --set-default-ca --server letsencrypt

# 3. Register the LE account with a REAL email.
#    Skipping this (or a placeholder) triggers:
#      "contact email has forbidden domain example.com"
/root/.acme.sh/acme.sh --register-account --server letsencrypt -m you@yourschool.org
```

### Namecheap DNS-01 — two possible paths

Namecheap gates API access behind an eligibility requirement: account
needs **20+ domains, a $50 balance, or $50 spent in the last 2 years**.
**Need to check whether the school's Namecheap account qualifies** —
that decides which path below applies.

**Path A — account qualifies for API access (fully automated):**
```bash
# 1. Enable API access in Namecheap: Profile → Tools → API Access
#    Whitelist the VPS's public IP there too.

# 2. Set credentials
export NAMECHEAP_API_KEY="..."
export NAMECHEAP_USERNAME="..."
export NAMECHEAP_SOURCEIP="<vps-public-ip>"

# 3. Issue — fully automated, no manual DNS steps.
#    --keylength ec-256 puts the cert in /root/.acme.sh/lhpscs.com_ecc/
#    (where the install wrapper looks); quote '*' so the shell doesn't glob it.
acme.sh --issue --dns dns_namecheap -d lhpscs.com -d '*.lhpscs.com' \
  --keylength ec-256 --reloadcmd /root/hestia-push-wildcard-cert.sh
```
acme.sh saves the NAMECHEAP_* creds + reloadcmd into its config and renews
automatically (~60 days) with no further input — the `export`s above are only
needed for this first issue.

**Path B — account doesn't qualify (manual DNS, still fine at this scale):**
```bash
acme.sh --issue -d lhpscs.com -d '*.lhpscs.com' --dns --keylength ec-256 \
  --yes-I-know-dns-manual-mode-enough-go-ahead-please
```
Prints two `_acme-challenge.lhpscs.com` TXT records to paste into
Namecheap's DNS panel by hand, then rerun the same command to finalize.
Only touches DNS once per ~90-day renewal cycle (not per student), so
manual is genuinely workable here — just needs a calendar reminder.

### Installing the cert into Hestia (either path)

Hestia's `v-add-web-domain-ssl` can't be pointed straight at the acme.sh
dir: it looks for cert files named after the web domain
(`<domain>.crt`/`.key`), while acme.sh stores `fullchain.cer`/`lhpscs.com.key`
— so it fails with exit 3 (E_NOTEXIST). The fix is a box-side wrapper,
`/usr/local/hestia/bin/v-add-web-domain-ssl-wildcard USER DOMAIN [BASE]`,
that stages the wildcard files under domain-named files in a temp dir and
then calls `v-add-web-domain-ssl` (or `v-update-web-domain-ssl` if SSL is
already on). See `webserver-runbook.md` for the wrapper script itself.

```bash
v-add-web-domain-ssl-wildcard <username> <username>.lhpscs.com lhpscs.com
```
Same wildcard cert reused for every student — not a new cert request per
student. The app calls this wrapper automatically at provision time
(`HestiaClient.install_ssl_wildcard`, part of `provision_webserver --personal`),
and its command name must be in the API key's profile.

### Renewal automation

Because this cert lives outside Hestia's native LE flow, Hestia's own
daily auto-renew cron won't touch it. A `--reloadcmd` script that acme.sh
calls after every issue/renew re-pushes the refreshed cert to each student
account. The account list is pulled **live from the app's roster endpoint**
(`/webserver/ssl_roster/`, bearer-token auth) — no hand-maintained
`student-list.txt`:

```bash
#!/bin/bash
# /root/hestia-push-wildcard-cert.sh
ROSTER_URL="https://tr.canora.us/webserver/ssl_roster/"
TOKEN="…"   # matches HESTIA_ROSTER_TOKEN in the app env

curl -fsS -H "Authorization: Bearer $TOKEN" "$ROSTER_URL" | while read -r user domain; do
  [ -n "$user" ] && /usr/local/hestia/bin/v-add-web-domain-ssl-wildcard "$user" "$domain" lhpscs.com
done
systemctl reload nginx
```
(The wrapper picks add-vs-update per domain, so the same script works for the
first install and every renewal.)
Attach with `--reloadcmd /root/hestia-push-wildcard-cert.sh` on the issue
command. The roster lists only provisioned personal accounts (shark-tank
domains carry their own per-domain certs, renewed by Hestia's native cron).
New mid-year students appear in the roster automatically — and already get
the wildcard cert at provision time — so nothing needs manual syncing.

## Open items (box-side setup + go-live)

1. Confirm Namecheap account API eligibility → choose Path A or B above.
2. Issue the wildcard cert on the box via acme.sh (DNS-01). The app installs
   it per account; acme.sh issuance itself is a one-time box-side setup.
3. Create a restricted Hestia API access key and open/firewall :8083 to the
   app host; set `HESTIA_*` env in the app and verify with
   `manage.py hestia_check`.
4. Confirm the SFTP port + chroot doc-root baked into students' `sftp.json`
   (defaults: port 22, `/web/<domain>/public_html`) against the live box;
   override via `HESTIA_SFTP_PORT` if needed.
5. Point each shark-tank project's real domain DNS at the VPS before running
   `provision_webserver --shark-ssl`.
6. Set `HESTIA_ROSTER_TOKEN` and drop `hestia-push-wildcard-cert.sh` in as the
   acme.sh `--reloadcmd`.

Resolved: bulk provisioning is the app's `provision_webserver` command
(dry-run built in), superseding the CSV/CLI loop; the reloadcmd pulls its
roster from the app, so there's no `student-list.txt` to keep in sync.