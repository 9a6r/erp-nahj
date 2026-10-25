# Desktop development

Nahj Desktop uses Python 3, GTK 4 and WebKitGTK 6. Web content has no native command bridge. Account sessions use persistent, server-specific WebKit stores. The application uses the operating system trust store and does not override TLS verification or disable the WebKit sandbox.

## Source checks

```bash
cd desktop
PYTHONPATH=. python3 -m unittest discover -s tests -v
python3 -m nahj_desktop --check
```

On Arch install `xorg-server-xvfb xorg-xauth dbus` for headless GUI tests:

```bash
PYTHONPATH=. dbus-run-session -- xvfb-run -a python3 tests/smoke_gui.py
```

The native smoke test exercises connection discovery, settings persistence, WebKit rendering, navigation, cancellation of stale requests and preservation of the current page when opening settings. Run it as an ordinary user in an environment that permits WebKit sandbox namespaces. Some restricted containers do not support these namespaces; such containers cannot validate the production sandbox.

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

Before distributing a release, check the following on a supported Arch installation:

- Install, upgrade and remove the package with pacman as a normal desktop user.
- Start from the application launcher on Wayland and X11.
- Verify Arabic and English, keyboard focus and a 1366×768 display at normal scale and fractional scaling.
- Connect to an ERPNext 17 test site; verify login, logout, permissions, forms and bank reconciliation.
- Import a statement, download a report, print a document and check file selection dialogs.
- Interrupt the network and reconnect without losing unsaved fields by merely opening settings.
- Validate enterprise certificates and any required SSO integration separately. Automatic cross-origin SSO redirects are currently delegated to the organization browser.

The visual palette takes inspiration from the NAHJ Blue Glass Plymouth theme and the Nahj shell: deep-water backgrounds, blue-grey surfaces and ice-blue highlights. No boot theme, compositor configuration, startup animation or system appearance is installed or changed by this application.
