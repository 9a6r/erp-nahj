#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
version=0.3.0
mkdir -p dist
# The archive contains source and documentation only; no local state or sessions.
tar --exclude=__pycache__ --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner \
    -cf - nahj_desktop nahj-desktop Makefile io.nahj.Desktop.desktop io.nahj.Desktop.svg README.md DEVELOPMENT.md SERVER.md \
    -C .. license.txt | gzip -n > "dist/nahj-desktop-$version.tar.gz"
checksum=$(sha256sum "dist/nahj-desktop-$version.tar.gz" | cut -d' ' -f1)
cat > dist/PKGBUILD <<EOF
pkgname=nahj-desktop
pkgver=$version
pkgrel=1
pkgdesc='Nahj business workspace for ERPNext'
arch=('any')
url='https://github.com/9a6r/erp-nahj'
license=('GPL-3.0-only')
depends=('python' 'python-gobject' 'gtk4' 'webkitgtk-6.0' 'gst-plugins-good' 'noto-fonts' 'adwaita-icon-theme')
optdepends=('xdg-desktop-portal: desktop integration on Wayland'
            'podman: local server and external MariaDB modes'
            'podman-compose: manage local server services'
            'slirp4netns: rootless container networking'
            'fuse-overlayfs: rootless container storage fallback')
source=("nahj-desktop-$version.tar.gz")
sha256sums=('$checksum')
package() {
    make DESTDIR="\$pkgdir" install
}
EOF
printf 'Package sources ready in desktop/dist.\n'
