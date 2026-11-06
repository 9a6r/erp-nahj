#!/usr/bin/env bash
# Called as the ordinary test user in an explicitly disposable Arch VM.
set -euo pipefail
cd "$HOME/source/desktop"
[[ $(id -u) != 0 ]]
uname -r | grep -q zen
# This disposable user has no containers yet. Exercise the actual installer
# starting without subordinate IDs, as on a newly prepared desktop account.
sudo sed -i '/^nahj:/d' /etc/subuid /etc/subgid
bash install.sh --with-server --yes
test "$(podman info --format '{{.Host.Security.Rootless}}')" = true
test -s /usr/share/applications/io.nahj.Desktop.desktop
test -s /usr/share/icons/hicolor/scalable/apps/io.nahj.Desktop.svg
echo 'PASS: actual Arch installer configured rootless Podman and installed the desktop launcher'
PYTHONPATH=. python -m unittest discover -s tests -p 'test_*.py' -v
export PYTHONPATH=.
export WEBKIT_DISABLE_DMABUF_RENDERER=1
timeout 240 xvfb-run -a -s '-screen 0 1280x820x24' dbus-run-session -- bash -c '
set -e
openbox >/tmp/nahj-openbox.log 2>&1 & wm=$!
trap "kill $wm" EXIT
python tests/smoke_gui.py
python tests/smoke_server_settings.py
python tests/smoke_language.py
python tests/smoke_download.py
'
timeout 180 dbus-run-session -- bash -c '
set -e
weston --backend=headless --renderer=pixman --socket=wayland-nahj --idle-time=0 >/tmp/nahj-weston.log 2>&1 & compositor=$!
trap "kill $compositor" EXIT
for i in {1..30}; do [[ -S "$XDG_RUNTIME_DIR/wayland-nahj" ]] && break; sleep 1; done
export WAYLAND_DISPLAY=wayland-nahj GDK_BACKEND=wayland
python tests/smoke_gui.py
python tests/smoke_language.py
'
bash package.sh
cd dist
makepkg --force --noconfirm
package=$(find . -maxdepth 1 -name '*.pkg.tar.zst' -print -quit)
sudo pacman -U --noconfirm "$package"
nahj-desktop --check
export XDG_CONFIG_HOME="$HOME/package-preferences"
PYTHONPATH=/usr/share/nahj-desktop python -c 'from nahj_desktop.config import save; save({"language":"ar","server":"https://erp.example.test"})'
before=$(sha256sum "$XDG_CONFIG_HOME/nahj/settings.json")
sudo pacman -U --noconfirm "$package"
sudo pacman -R --noconfirm nahj-desktop
test "$before" = "$(sha256sum "$XDG_CONFIG_HOME/nahj/settings.json")"
echo 'PASS: pacman build/install/reinstall/remove preserves preferences'
cd ..
redis_image=$(PYTHONPATH=. python -c 'from nahj_desktop.server import REDIS_IMAGE; print(REDIS_IMAGE)')
podman run -d --name nahj-arch-persistence -v nahj-arch-data:/data "$redis_image" redis-server --appendonly yes
for _ in {1..30}; do podman exec nahj-arch-persistence redis-cli ping && break; sleep 1; done
podman exec nahj-arch-persistence redis-cli SET nahj-persistence survives-reboot
podman stop nahj-arch-persistence
echo 'PASS: rootless Podman writes persisted test data before reboot'
