# Nahj Desktop 0.2.1 — verification

Validated on 26 October 2026 using an Arch Linux x86_64 virtual machine under QEMU, with its own Linux 7.2.11 kernel, 2 virtual CPUs and 3 GiB RAM. The runtime was GTK 4.24.1 and WebKitGTK 2.54.2. WebKit sandboxing and TLS verification remained enabled.

## Checks

| Area | Verification |
| --- | --- |
| Desktop configuration and installer | 11 automated tests: URL validation, private preferences, corrupt configuration, graphics preference, discovery, redirects, interrupted dependency installation and package build failures |
| X11 | Native window, Arabic/English, visible WebKit dimensions, stylesheet application on a local server port, connection, navigation, stale callbacks, storage failure recovery and preservation of the current page |
| Wayland | The same native smoke test inside headless Weston |
| Files | Real WebKit download through the native file chooser; saved bytes matched the server response; cancelling a second download preserved the first file |
| Banking build | Production Vite build and TypeScript project checks |
| JavaScript regressions | 13 tests passed |
| Account language | 4 backend tests passed, including guest denial and invalid language rejection |
| Real ERPNext session | Authenticated Banking in Arabic/RTL and English/LTR; Arabic Desk; customer creation, retrieval, update and deletion from WebKit; test session signed out |
| Package lifecycle | Pacman upgrade, removal and reinstallation; all 26 installed files present; preferences and a session-data marker preserved |

The X11 visual review uses Openbox and a virtual display. ERPNext screenshots use the graphics compatibility setting because the virtual display does not provide the DMA-BUF rendering path. This setting does not disable the WebKit sandbox. The screenshots are captures of the installed application, not mockups.

## Changes verified

- Web content expands to fill the desktop window; a successfully loaded but zero-height page is now rejected by the GUI test.
- Workspace navigation uses `/desk`, the Frappe 17 route.
- Downloads pass a local filesystem path to WebKit 6 and report unsupported save destinations.
- `gst-plugins-good` is included for the media backend used by ERPNext's notification sounds.
- A failed storage operation keeps the existing workspace and saved server intact.
- A stopped web process presents a retry action.
- Banking asks for a company before requesting company-specific accounts; the company selector shows its current selection correctly.
- Arabic web content uses the same readable Noto Sans Arabic family as the native window.
- Stylesheet injection also works for servers with explicit ports.
- Frappe 17 Desk uses the Nahj blue Espresso color tokens on screen; print styles remain controlled by the server.
- The source installer installs its rebuilt package even when its version number is unchanged.

## Distribution and size

The ready-made Arch package is approximately 35 KiB, with approximately 77 KiB of installed application files. System libraries, font packages, user sessions and the ERPNext server are separate. Pacman shows the actual additional download and disk space for each machine before installation.

The package reuses system GTK, WebKit and fonts. It does not bundle another browser runtime, require `base-devel` for installation, or require downloading ERPNext's Git history. No ERPNext modules, Arabic fonts, visual effects or application features were removed to reduce the download.

## Scope

These checks cover the desktop integration and the changed Banking behavior. They are not an exhaustive validation of every ERPNext workflow, external banking service, printer or enterprise identity provider. QEMU was used for the Arch guest; the user's particular EndeavourOS ISO and VirtualBox graphics configuration were not reproduced. Automatic cross-origin SSO still requires the organization browser, as described in the user guide.

The client requires an initialized ERPNext/Frappe 17 server. First-time server setup remains the server administrator's responsibility. Hardware acceleration performance cannot be inferred from a software-emulated test machine.
