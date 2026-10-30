# Nahj 0.3.1-rc1 — verification, 30 October 2026

**Release status: not published; not yet approved for company production use.**
The stable server now passes real business, persistence and recovery checks. The
current desktop package still needs native Arch/Linux Zen validation, and the
upstream Arabic catalogues are incomplete.

## Source and artifact identity

- Review base: merged PR #1, `adb2b243ad1816843f7c8497b93b31f34d2e7b29`.
- ERPNext: stable **16.53.0**, upstream `9cd11b19575bfc34f092a24f6c8b368c4dd69481`.
- Frappe: stable **16.54.0**, upstream `2fcb9397a1f1da353b21e53d2f97ec56653acd02`.
- Official amd64 base manifest: `sha256:8f454efa71e9ffad9de4b9ccf377566134d285612f19e1e12e8a43fe7bf0db75`.
- Nahj image: `sha256:787360f503b4c1cac2167d3ceb1210fa4a8a9ae6f5c931759f1d2a893558af25`.
- Archive: `nahj-server-0.3.1-rc1-amd64.tar.gz`, **1,091,060,459 bytes**.
- Archive SHA256: `dd571a8003e208f521b3edd121fd1343a7b0eab360b16475b28b11034d50c9d0`.

The large diff against develop replaces the development snapshot with the exact
stable upstream tree. Relative to the stable ERPNext tree, business application
code changes are limited to the existing banking language endpoint and its test;
the Nahj frontend customization and desktop live separately. This does not strip
upstream ERPNext modules or replace accounting/stock logic with demonstrations.
The runtime printing bridge is shipped in the desktop package and mounted by the
controller; it is not an unrecorded change to the image archive.

## Checks performed

| Check | Result |
| --- | --- |
| Desktop Python regression suite | **32 passed**, including real loopback HTTP forwarding, image archive deduplication, image identity, backup integrity, locking, recovery and download verification |
| Banking language tests against real ERPNext database | **4 passed** |
| Banking frontend | Frozen-lockfile dependency installation and production build passed |
| Desktop package source | Source archive, shell syntax, isolated `make install`, and installed release-manifest checks passed; this is not a native pacman lifecycle test |
| Stable site provisioning | Real MariaDB and Redis; Frappe and ERPNext installed from scratch |
| Company setup | Original Frappe/ERPNext setup workflow created a disposable company |
| Business records | Arabic customer and supplier, real stock item and stock receipt |
| Sales and payment | Submitted sales invoice for 240 EGP, balanced GL entries, submitted payment, zero outstanding balance |
| Purchasing and stock | Submitted purchase invoice for 120 EGP; stock quantity verified at 11 after receipt, sale and purchase |
| Permissions | Restricted user cannot read sales invoices; unauthenticated HTTP cannot fetch a private attachment |
| HTTP | Valid login, rejection of invalid login, public/private file contents, banking assets, Arabic RTL and English LTR markup, integrations route |
| Background work | Real queued job completed; scheduler enabled |
| Backup | Controller exported SQL, public/private files, site/common configuration, profile, Compose configuration and a verified checksum manifest |
| Independent restore | SQL restored to a separate database/site; submitted invoices, settled balance, stock and both attachment contents verified |
| Restart | Original and restored records and attachments survived explicit stop/start; HTTP checks passed again; the managed environment also restarted between the two work sessions |
| External MariaDB preflight | Valid verified TLS connection accepted; wrong password, untrusted CA, hostname mismatch and nonempty database rejected |
| Full external database setup | Frappe and ERPNext installed in a separate MariaDB database over verified TLS; Arabic ToDo and public/private attachments saved |
| External dump/restore | Native MariaDB dump and restore succeeded with CA and hostname verification; independent restored database contained the Arabic record and attachment metadata |
| Invoice PDF | Real submitted invoice generated after repairing internal asset connectivity, including after service restart; one-page PDF rendered and visually inspected with Arabic heading/customer and RTL layout. Mixed English labels/amount-in-words still need localization review |

`tests/integration_business.py` contains the real transaction checks. It requires
an explicitly disposable site and the `nahj_disposable_test_site` site setting;
it must never be run on a production company database. The validation company and
transactions are test data only and are not included in the distributed image.

## Printing repair

The first PDF attempt failed with `ConnectionRefusedError`: the canonical desktop
URL pointed at the host's loopback port, which is not reachable as loopback from a
backend container. `nahj_desktop/runtime.py` now starts an internal loopback bridge
for backend and worker processes, forwarding only to the private frontend service.
This keeps public/canonical links and session-cookie origins unchanged. It does
not expose a public proxy, use host networking, or weaken TLS or renderer security.
Port 8000 is reserved for Gunicorn; the managed public port must be different.

## Scope and limitations of this environment

The new checks ran on Linux **6.18.55**, Docker **28.4.0**, VFS storage, with a
32 GiB writable disk. This is **not** an Arch/Zen machine and does not validate
rootless Podman or the current native GTK/WebKit UI.

The upstream multilayer pull exhausted VFS space and was cleaned up by Docker.
The new builder produces a single-layer archive and rejects duplicate tar paths.
Even with one layer, VFS copies the filesystem for every container. To fit the
budget, the validation backend ran real Gunicorn, nginx, WebSocket, worker and
scheduler processes in one container, while MariaDB and Redis were separate.
Production `compose_spec()` continues to separate those application services.
For this consolidated test only, the frontend hostname pointed to its co-located
nginx. The external provisioning container was reused for database and backup
checks; label-based backend discovery was independently exercised on the local
stack. These adaptations are not evidence that the full production Podman
topology has passed native validation.

Historical Zen screenshots and 0.3.0 checks remain available in
`VERIFICATION-0.3.0.md`; they must not be presented as new 0.3.1 test results.

## Arabic coverage and remaining release gates

Catalogue audit of the pinned sources found:

| Catalogue | Entries | Translated | Untranslated |
| --- | ---: | ---: | ---: |
| ERPNext Arabic | 11,102 | 10,438 | 664 |
| Frappe Arabic | 7,937 | 6,091 | 1,846 |

These are catalogue counts, not a visual or linguistic quality score. Matching
translations from the available upstream development catalogues did not fill the
remaining entries. Nahj lifecycle messages and integration navigation have Arabic
labels, but **the entire ERP is not fully translated**.

Before publication:

1. Validate this exact desktop source on Arch/Linux Zen: rootless Podman setup,
   service separation, Wayland/X11 WebKit sandboxing, native file dialogs,
   pacman install/reinstall/removal and machine reboot persistence.
2. Review the remaining Arabic catalogue entries, terminology, forms, reports,
   print layouts and mixed Arabic/English data visually.
3. Validate the organization's chosen external providers, SMTP/OAuth/SSO flows,
   roles, backup destination and operational recovery procedure with its actual
   configuration. No provider integration was claimed merely from displaying
   an API-key input.
4. Publish only the archive matching `server_release.json` after those gates
   pass. Keep `published: false` until then. Never downgrade an existing ERPNext
   17 database to this stable 16 image.
