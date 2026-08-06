# HestiaCP Student Hosting Setup — lhpscs.com

Reference notes for a self-hosted HestiaCP environment providing ~100 middle
school students (MS CS 1, web design class) with FTP/SFTP access to publish
static/dynamic web content. Carried over from a prior conversation; picking
up here with SSL as the next task (not yet started).

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

## Account provisioning (in progress)

Plan is bulk creation from this site via Hestia's CLI

```bash
# one-time: a "student" package to keep accounts minimal
# (disk quota ~250-500MB, max web domains = 1, max mail/DNS/DB = 0)

# per student:
v-add-user <username> '<password>' <email> student_package <first> <last>
v-add-web-domain <username> <username>.lhpscs.com
```

Not yet built: the actual loop/script reading the spreadsheet and calling
these commands per row, with a dry-run mode. Also not yet decided: exact
package limits.

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

# 3. Issue — fully automated, no manual DNS steps
acme.sh --issue --dns dns_namecheap -d lhpscs.com -d *.lhpscs.com
```
acme.sh installs its own daily cron and renews automatically (~30 days
before expiry) using the same credentials.

**Path B — account doesn't qualify (manual DNS, still fine at this scale):**
```bash
acme.sh --issue -d lhpscs.com -d *.lhpscs.com --dns \
  --yes-I-know-dns-manual-mode-enough-go-ahead-please
```
Prints two `_acme-challenge.lhpscs.com` TXT records to paste into
Namecheap's DNS panel by hand, then rerun the same command to finalize.
Only touches DNS once per ~90-day renewal cycle (not per student), so
manual is genuinely workable here — just needs a calendar reminder.

### Installing the cert into Hestia (either path)

```bash
v-add-web-domain-ssl <username> <username>.lhpscs.com /root/.acme.sh/lhpscs.com_ecc/
v-add-web-domain-ssl-force <username> <username>.lhpscs.com
```
Same cert/key files reused for every student — not a new cert request
per student. This loop belongs in the bulk-provisioning script.

### Renewal automation (needs building)

Because this cert lives outside Hestia's native LE flow, Hestia's own
daily auto-renew cron won't touch it. Plan: a `--reloadcmd` script that
acme.sh calls automatically after every issue/renew, looping over a
maintained list of student accounts and re-pushing the refreshed cert:

```bash
#!/bin/bash
# /root/hestia-push-wildcard-cert.sh
CERT_DIR="/root/.acme.sh/lhpscs.com_ecc"
while read -r student; do
  v-update-web-domain-ssl "$student" "${student}.lhpscs.com" "$CERT_DIR"
done < /root/student-list.txt
systemctl reload nginx
```
Attach with `--reloadcmd /root/hestia-push-wildcard-cert.sh` on the
issue command. Open question: how `student-list.txt` gets kept in sync
with new mid-year student accounts (ideally auto-appended at provisioning
time so new students get the cert pushed immediately rather than waiting
for the next renewal cycle).

## Open items

1. Confirm Namecheap account API eligibility → choose Path A or B above
2. Build the wildcard cert issuance + install flow end-to-end
3. Build/wire up `hestia-push-wildcard-cert.sh` as the reloadcmd
4. Decide how new-student onboarding keeps `student-list.txt` in sync
5. (Separately, still pending from provisioning) finish the bulk
   CSV-driven `v-add-user` / `v-add-web-domain` script with dry-run mode