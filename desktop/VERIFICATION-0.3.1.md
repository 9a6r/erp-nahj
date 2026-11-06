# Nahj 0.3.1-rc1 — verification, 30 October 2026

**Release status: not published; not yet approved for company production use.**
The stable server passes real business, persistence and recovery checks. The
desktop and full ERP deployment pass the native Arch/Linux Zen checks described
below, including rootless Podman backup/recovery and a complete VM reboot.
The completed Arabic catalogues are embedded in the rebuilt, unpublished image,
which has now passed the full native lifecycle revalidation below.

## Arabic image revalidation — reviewed 6 November 2026

Source commit `acb567d47d278480e346dc0718eb50b3bbcde9d9` passed both workflows
on 5 November (logs reviewed on 6 November):

- [Full ERP on rootless Arch/Zen](https://github.com/9a6r/erp-nahj/actions/runs/42079406329),
  job `127428179959`: CI reproduced the new image ID, archive SHA256 and size
  exactly. Eight separate services completed the business transactions, access
  checks, Arabic SMTP/webhook delivery, backup and independent recovery.
- The actual Arabic gettext and Standard print checks passed on the original
  site, the restored review site, after recovery activation, and on both sites
  after a complete Zen VM reboot. Arabic/English amount-in-words did not alter
  stored posted invoices, purchase invoices or payment entries. HTTP invoice PDFs
  and attachment authorization passed at each stage.
- [Native desktop on Arch/Zen](https://github.com/9a6r/erp-nahj/actions/runs/42079406577),
  job `127428180059`: all 40 then-current unit tests, GTK settings, X11 and Wayland
  WebKit, saved Arabic/English language with session/CSRF, native download/save/
  cancellation, pacman install/reinstall/remove and rootless volume persistence
  across reboot passed.

This evidence covers the current server image identity below. It does not certify
the user's physical GPU/compositor, every ERP form/report or live third-party
provider configuration. The later desktop-only diagnostic translation change
adds coverage for wrapped helper errors without changing the server image.

## Full rootless ERP follow-up — 5 November 2026

The full-stack workflow rebuilds the server from the pinned source and checks
its image ID, archive SHA256 and size against the existing release manifest.
This reproduction **passed** in CI; no different server artifact was substituted.
The first real rootless attempt provisioned MariaDB and installed ERPNext, then
exposed an image-ID representation bug: Podman returned the verified digest
without `sha256:`, while the start guard expected that prefix. Commit
`c4723711df3d` canonicalizes the verified ID and reads equivalent saved profiles
without permitting a different image. The added regression failed before the
fix; all 40 desktop tests pass with it.

The next run reached recovery activation but exposed stale frontend upstream
resolution after backend/WebSocket restart. Commit `6eebbb24cc` restarts the
frontend after those services. The [full-stack run at that commit](https://github.com/9a6r/erp-nahj/actions/runs/42028088123)
**passed** on 5 November 2026 under Linux `7.2.14-zen1-1-zen`:

- Actual Server controller with eight separate rootless Podman containers.
- Submitted sales/purchase/payment records, balanced ledger, stock quantity 11,
  attachment hashes, restricted-user denial and encrypted canary decryption.
- Actual HTTP login/denial, private-file authorization, saved Arabic/English
  preference, banking assets and generated invoice PDF.
- Real Arabic SMTP delivery and signed webhook from the worker to isolated
  receivers on the private service network, before and after recovery.
- Backup and independent restore, review mode with worker/scheduler paused,
  explicit activation and verified data/permissions after activation.
- Complete Zen VM shutdown/boot, then verification of both original and restored
  full stacks, including business data, files, encryption and HTTP/PDF checks.

The run reproduced the old pinned server archive exactly. It does not validate
the later Arabic catalogue changes or the user's actual compositor/hardware.

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
the separate full rootless ERP recovery/reboot result is recorded at the top of
this report.

The local extracted WebKit runtime could not launch its subprocesses within this
managed workspace; no sandbox bypass was used. The screenshot evidence is GTK
on Debian/X11; the native Arch result comes from the independent VM run above.

## Source and artifact identity

- Review base: merged PR #1, `adb2b243ad1816843f7c8497b93b31f34d2e7b29`.
- ERPNext: stable **16.53.0**, upstream `9cd11b19575bfc34f092a24f6c8b368c4dd69481`.
- Frappe: stable **16.54.0**, upstream `2fcb9397a1f1da353b21e53d2f97ec56653acd02`.
- Official amd64 base manifest: `sha256:8f454efa71e9ffad9de4b9ccf377566134d285612f19e1e12e8a43fe7bf0db75`.
- Current Arabic image: `sha256:dd42ba26bfb096e4079ad6bd71ea4bd1ee60293cfc8d6bbf67d3da977d161127`.
- Archive: `nahj-server-0.3.1-rc1-amd64.tar.gz`, **1,091,253,026 bytes**.
- Archive SHA256: `fb02ce817ec842551cb670e2caa88ccebc783fcbaced97f406a235a1aca34163`.

The earlier full-stack run at `6eebbb24cc` used image
`sha256:787360f503b4c1cac2167d3ceb1210fa4a8a9ae6f5c931759f1d2a893558af25`,
archive SHA256 `dd571a8003e208f521b3edd121fd1343a7b0eab360b16475b28b11034d50c9d0`
(1,091,060,459 bytes). The new image has its own passing run recorded above.
Neither candidate has been published; automatic migration of
existing profiles/backups across image identities remains unsupported.

The original stabilization replaced the development snapshot with the stable
upstream tree. The overlays add the banking language endpoint/frontend, Arabic
catalogues and print-language formatting described above; the desktop lives
separately. This does not strip
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

The pinned sources originally had 664 missing ERPNext entries and 1,846 missing
Frappe entries. The Nahj source now fills all of them, repairs broken placeholders
and removes repeated English suffixes in legacy error translations. Three runtime
Egyptian currency strings are also included. Source catalogue checks now report:

| Catalogue | Entries | Translated | Untranslated |
| --- | ---: | ---: | ---: |
| ERPNext Arabic | 11,105 | 11,105 | 0 |
| Frappe Arabic | 7,937 | 7,937 | 0 |

These are catalogue counts, not a visual or linguistic quality score. The builder
checks missing/fuzzy messages, interpolation, HTML/Jinja tokens and actual compiled
gettext lookup, including message contexts. It embeds both PO and MO files in the
server image. Brand names and executable examples intentionally retain their
spelling; user-entered text and third-party app messages are not rewritten.

On the disposable recovered Docker site, actual Frappe lookups and Standard print
HTML passed. Sales invoices, purchase invoices and payment entries rendered their
amount-in-words in Arabic and English while stored posted records stayed unchanged.
The real PDF was regenerated and [visually inspected](screenshots/0.3.1/invoice-ar-completed.png):
Arabic amount/unit labels, translated units, Egyptian currency symbol and Arabic
amount-in-words are visible. This is not a visual review of all forms/reports.
The rebuilt image subsequently passed the full Arch/Zen lifecycle checks recorded
at the top of this report. The local suite now has 42 passing tests, including
wrapped helper error translation and preservation of unknown technical diagnostics.

Before production adoption (the tested candidate may be published as a prerelease):

1. Repeat full rootless ERP validation for each new server artifact. The complete
   stack at `6eebbb24cc` passed backup/recovery and reboot above. Validate the
   user's actual compositor/GPU and remaining file dialogs separately.
2. Continue linguistic and visual review of terminology, forms, reports, print
   layouts and mixed Arabic/English data; catalogue coverage alone is insufficient.
3. Validate the organization's chosen external providers, SMTP/OAuth/SSO flows,
   roles, backup destination and operational recovery procedure with its actual
   configuration. No provider integration was claimed merely from displaying
   an API-key input.
4. Publish only the archive matching `server_release.json` after automated native
   and full ERP checks pass. The release workflow gates publication on both jobs.
   Organization-specific checks above remain requirements before production
   adoption, not claims made by a prerelease. Never downgrade an existing ERPNext
   17 database to this stable 16 image.

## Source audit and installation follow-up

The new source audit is recorded in [UPSTREAM-AUDIT.md](UPSTREAM-AUDIT.md).
The local suite has 44 passing tests. Banking Vite build and TypeScript checking
passed after translating remaining reconciliation/import controls and accessibility
labels. The real Subcontracting Receipt print regression was reproduced before
the fix and passed afterward on the disposable Frappe site.

The new artifact uses image ID
`sha256:ac36bee5c50b0393741e099389e2a111b23f86e49c6f8bf22091be84d8842ad9`,
archive SHA256 `b24f5975c43cae48bc323c7e3eb4029e5739f8bf53a172861293cad503cee98b`,
and size 1,091,253,572 bytes. Previous image checks above are historical evidence;
the tag-triggered release must independently reproduce and validate this artifact.
Native validation now also exercises the actual installer, including subordinate
ID allocation on a fresh account. Publication remains gated on both CI jobs.
