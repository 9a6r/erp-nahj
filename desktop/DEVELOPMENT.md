# Desktop development

Nahj Desktop uses Python 3, GTK 4 and WebKitGTK 6. Web content has no native command bridge. Account sessions use persistent, server-specific WebKit stores. The application uses the operating system trust store and does not override TLS verification or disable the WebKit sandbox.

## Source checks

```bash
cd desktop
PYTHONPATH=. python3 -m unittest discover -s tests -v
python3 -m nahj_desktop --check
```

On Arch install `xorg-server-xvfb xorg-xauth dbus openbox xdotool imagemagick` for X11 GUI tests:

```bash
PYTHONPATH=. xvfb-run -a -s '-screen 0 1280x820x24' dbus-run-session -- bash -c '
openbox >/tmp/nahj-test-window-manager.log 2>&1 & wm=$!
trap "kill $wm" EXIT
python3 tests/smoke_gui.py && python3 tests/smoke_download.py
'
```

The native smoke test exercises connection discovery, settings persistence, visible WebKit allocation, navigation, recovery from storage errors, cancellation of stale requests and preservation of the current page when opening settings. The download test drives the native file chooser with keyboard events, checks the saved bytes and cancels a second download. Run as an ordinary user in an environment that permits WebKit sandbox namespaces. Some restricted containers do not support these namespaces; such containers cannot validate the production sandbox.

X11 captures need a window manager: without one, GTK can position an RTL window outside the visible screen. Use the same Xvfb/Openbox session with `python3 tests/capture_settings.py screenshot.png --language ar`. A virtual display without DMA-BUF support may require `WEBKIT_DISABLE_DMABUF_RENDERER=1`, the same rendering option exposed by `nahj-desktop --graphics-compatibility`. This does not disable the WebKit sandbox.

For Wayland, run the smoke test inside a compositor session with `GDK_BACKEND=wayland`. A headless Weston session can use its `headless` backend and `pixman` renderer. This checks the Wayland path; it does not measure hardware performance or cover every compositor.

## Package checks

```bash
./package.sh
cd dist
makepkg --syncdeps --cleanbuild
pacman -Qip nahj-desktop-*.pkg.tar.zst
```

The source archive is reproducible and contains no local application data. The package carries an archive checksum, documentation, license, desktop entry and scalable icon. Installing an update does not change the user's settings or session directories.

## Banking web application

```bash
cd banking
yarn install --frozen-lockfile
yarn build
```

Use `FRAPPE_SITE_NAME=<site> yarn dev` for the development proxy. `FRAPPE_WEBSERVER_PORT` defaults to 8000. `FRAPPE_BENCH_PATH` optionally reads the Bench configuration.

From the Bench directory, after installing or updating the ERPNext app:

```bash
bench --site <site> execute frappe.gettext.translate.compile_translations --kwargs '{"target_app":"erpnext","locale":"ar"}'
bench --site <site> clear-cache
bench --site <site> run-tests --module erpnext.tests.test_banking_language --skip-before-tests --lightmode
```

## Release validation

The current results and remaining gates are in [VERIFICATION-0.3.1.md](VERIFICATION-0.3.1.md).
Build the pinned stable image using [server-image/README.md](server-image/README.md).
`tests/integration_business.py` creates real posted transactions and is only for
a disposable site with `nahj_disposable_test_site` explicitly enabled. Set
`NAHJ_ACCEPTANCE_SITE` to that site and run it with the bench virtualenv Python
from the bench's `sites` directory. Never run it against company data.

The renderer bridge in `nahj_desktop/runtime.py` is mounted by the desktop
controller. It forwards a backend/worker container's canonical loopback HTTP
port to the private frontend, retaining canonical URLs and cookies for PDF
assets. It is not an externally listening proxy. Port 8000 is reserved for the
application backend. Validate PDF generation after service restart as well as
initial startup.

Before distributing a release, check the following on a supported Arch installation:

- Install, upgrade and remove the package with pacman as a normal desktop user.
- Start from the application launcher on Wayland and X11.
- Verify Arabic and English, keyboard focus and a 1366×768 display at normal scale and fractional scaling.
- Connect to an ERPNext 16.53 / Frappe 16.54 test site; verify login, logout, permissions, forms and bank reconciliation.
- Import a statement, download a report, print a document and check file selection dialogs.
- Interrupt the network and reconnect without losing unsaved fields by merely opening settings.
- Validate enterprise certificates and any required SSO integration separately. Automatic cross-origin SSO redirects are currently delegated to the organization browser.

The visual palette takes inspiration from the NAHJ Blue Glass Plymouth theme and the Nahj shell: deep-water backgrounds, blue-grey surfaces and ice-blue highlights. No boot theme, compositor configuration, startup animation or system appearance is installed or changed by this application.
