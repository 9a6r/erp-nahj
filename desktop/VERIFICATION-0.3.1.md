# Nahj 0.3.1-rc1 — verification, 30 October 2026

**Release status: not published; not yet approved for company production use.**
The stable server passes real business, persistence and recovery checks. The
desktop passes the native Arch/Linux Zen checks described below. Full ERP
deployment under rootless Podman still needs validation, and the upstream Arabic
catalogues are incomplete.

## Follow-up validation — 5 November 2026

The recovery/language implementation was merged in PR #3 (`5168d00df91b`),
and the [seven current screenshots](screenshots/0.3.1/README.md) in PR #4
(`5e056863103d`). The server image and archive identity below are unchanged.

| Additional check | Result |
| --- | --- |
| Desktop Python regression suite | **40 passed**, including backup validation and real HTTPS certificate/hostname rejection |
| Controller-driven recovery | Restored the verified SQL, public/private files and original encryption material into a separate local project; posted invoices, zero outstanding balance, stock quantity 11, attachment contents and original Administrator login verified |
| Recovery activation | Scheduler and outbound email paused for review; explicit activation enabled them and a real worker completed a queued job; records and attachment contents survived stop/start |
| Persistent Desk language | Authenticated user preference changed Arabic → English → Arabic through Frappe's actual API; subsequent Desk boot used the saved language each time |
| Banking database tests | **4 passed** again against the recovered site |
| Email and webhook | Actual Frappe Email Account delivered an Arabic MIME message to a loopback SMTP receiver; an actual document event and worker sent an Arabic webhook with a verified HMAC signature |
| GTK settings | Native GTK settings and language controls passed on Debian; captures include both connection languages and recovery/external-database controls |
| Documentation regression checks | **3 passed**; GitHub documentation and desktop/banking workflows passed for screenshot commit `646e68f074cb` |

The service tests use only disposable data and local receivers, not a live mail
provider or a customer's webhook. They do not validate every external provider.
The real backend checks still use the consolidated Docker validation topology
described below. They are not full rootless Podman topology validation.

The native Arch/Zen workflow runs a separate Arch VM, boots an installed Zen
kernel, and checks X11/Wayland WebKit, package lifecycle and rootless volume
persistence across reboot. The first attempt was cancelled when PR #3 merged.
The [rerun](https://github.com/9a6r/erp-nahj/actions/runs/41937584475) installed
the dependencies and booted **7.2.14-zen1-1-zen**, but failed before application
tests: direct kernel boot changed the interface from `eth0` to `ens3`, leaving
the cloud image's existing DHCP configuration unmatched. Commit `00c66b5a9098`
preserves interface naming; its
[replacement run](https://github.com/9a6r/erp-nahj/actions/runs/41985125581)
**passed** for source `00c66b5a909814f0aeeb08d12e11bb525848f606`.

| Native Arch/Zen check | Result |
| --- | --- |
| Guest environment | Linux `7.2.14-zen1-1-zen`, Python `3.14.9-1`, GTK `4.24.1-1`, WebKitGTK `2.54.2-1`, Podman `6.1.4-1`, podman-compose `1.6.0-1` |
| Desktop regressions | **40 passed** inside the Zen guest |
| X11/Openbox | Real WebKit window, stylesheet, navigation, connection, storage-error recovery, stale callback rejection and draft preservation passed |
| Language | GTK settings preservation and real WebKit Arabic/English persistence with session/CSRF passed; server rejection kept the previous settings and page |
| File download | Real WebKit download, native save destination, exact contents and cancellation passed |
| Wayland/Weston | Headless compositor: WebKit connection/lifecycle and authenticated language tests passed |
| Arch package | `makepkg`, pacman installation/reinstallation/removal and installed `--check` passed; removal preserved user preferences |
| Rootless storage | `rootless=true`, `storage=overlay`; Redis data on a named volume survived a full Zen VM shutdown and boot |

[Native evidence archive](https://github.com/9a6r/erp-nahj/actions/runs/41985125581/artifacts/13396505149)
contains the checksummed cloud-image identity, package log, per-boot serial logs,
native test output, reboot assertion and final environment versions. Wayland ran
headlessly with software rendering; Mesa reported unavailable Vulkan/Zink before
the UI tests passed. This does not validate hardware GPU drivers or the user's
exact Vitreus/compositor configuration. WebKit sandboxing was not disabled.

The harness now retains separate serial logs per boot, exposes SSH readiness
progress, and uses KVM when the disposable CI runner provides it. Its reboot
check now stops on a failed Redis value assertion. An isolated execution of
that actual shell command confirmed that a missing/wrong value exits nonzero
and never prints PASS. Pushes to `develop` run the native check independently
of pull-request closure; documentation and screenshot-only changes are excluded.

The 40 desktop tests, 4 real banking tests, 3 documentation tests, native GTK
settings test, restored business/file/login checks, authenticated language
changes, SMTP/webhook checks and invoice PDF generation were rerun successfully
after the follow-up testing request on 5 November.

This successful workflow does not exercise a complete ERP service deployment or
every native file-dialog interaction. Its reboot persistence check uses Redis;
it is not an ERP database recovery test. The separate real ERP recovery results
above ran on Docker.

The local extracted WebKit runtime could not launch its subprocesses within this
managed workspace; no sandbox bypass was used. The screenshot evidence is GTK
on Debian/X11; the native Arch result comes from the independent VM run above.

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

1. Validate a full ERP deployment on Arch/Linux Zen using rootless Podman and
   separate application services, including backup/recovery and reboot of that
   complete stack. Validate the user's actual compositor/GPU and remaining file
   dialogs. The native desktop/package/Redis-volume checks above have passed.
2. Review the remaining Arabic catalogue entries, terminology, forms, reports,
   print layouts and mixed Arabic/English data visually.
3. Validate the organization's chosen external providers, SMTP/OAuth/SSO flows,
   roles, backup destination and operational recovery procedure with its actual
   configuration. No provider integration was claimed merely from displaying
   an API-key input.
4. Publish only the archive matching `server_release.json` after those gates
   pass. Keep `published: false` until then. Never downgrade an existing ERPNext
   17 database to this stable 16 image.
