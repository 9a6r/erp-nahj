#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dist
tar --exclude=__pycache__ -czf dist/nahj-desktop-0.1.0.tar.gz nahj_desktop nahj-desktop Makefile io.nahj.Desktop.desktop io.nahj.Desktop.svg
checksum=$(sha256sum dist/nahj-desktop-0.1.0.tar.gz | cut -d' ' -f1)
cat > dist/PKGBUILD <<EOF
pkgname=nahj-desktop
pkgver=0.1.0
pkgrel=1
pkgdesc='Native Arabic ERPNext workspace for Linux'
arch=('any')
url='https://github.com/9a6r/erp-nahj'
license=('GPL-3.0-only')
depends=('python' 'python-gobject' 'gtk4' 'webkitgtk-6.0' 'noto-fonts')
source=("nahj-desktop-0.1.0.tar.gz")
sha256sums=('$checksum')
package() {
    make DESTDIR="\$pkgdir" install
}
EOF
printf 'Arch package sources created in desktop/dist; run makepkg -si there.\n'
