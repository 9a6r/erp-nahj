#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if (( EUID == 0 )); then
    printf 'Run this installer as your normal user, without sudo.\n' >&2
    exit 1
fi
if ! command -v pacman >/dev/null; then
    printf 'This installer supports Arch Linux and pacman-based distributions.\n' >&2
    exit 1
fi
printf 'Installing Nahj Desktop and its system dependencies with pacman.\n'
sudo pacman -Syu --needed base-devel python python-gobject gtk4 webkitgtk-6.0 noto-fonts adwaita-icon-theme
./package.sh
cd dist
makepkg --syncdeps --install --needed --force
printf '\nNahj is installed. Open it from the application menu or run nahj-desktop.\n'
