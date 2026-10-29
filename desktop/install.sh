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
if [[ -e /var/lib/pacman/db.lck ]]; then
    printf 'Pacman is locked. Wait for any running package operation to finish.\nDo not remove the lock while pacman is running.\n' >&2
    exit 1
fi

dependencies=(base-devel python python-gobject gtk4 webkitgtk-6.0 gst-plugins-good noto-fonts adwaita-icon-theme)
case "${1:-}" in
    --with-server) dependencies+=(podman podman-compose slirp4netns fuse-overlayfs) ;;
    '') ;;
    *) printf 'Usage: %s [--with-server]\n' "$0" >&2; exit 2 ;;
esac
missing=()
for dependency in "${dependencies[@]}"; do
    if ! pacman -Q "$dependency" >/dev/null 2>&1; then
        missing+=("$dependency")
    fi
done
if (( ${#missing[@]} )); then
    printf 'Installing missing dependencies: %s\n' "${missing[*]}"
    # Use the existing sync databases. Never refresh them without a full upgrade.
    # System upgrades are a separate, deliberate operation owned by the user.
    if sudo pacman -S --needed "${missing[@]}"; then
        :
    else
        status=$?
        printf '\nDependency installation stopped (exit %s). Nahj has not been installed.\n' "$status" >&2
        if (( status == 137 )); then
            printf 'The process was killed. Check available memory and disk space, and system logs.\n' >&2
        fi
        printf 'If mirrors report missing/outdated packages, finish a full system upgrade with sudo pacman -Syu, then rerun this installer.\nDo not use pacman -Sy alone or remove an active pacman lock.\n' >&2
        exit "$status"
    fi
fi
printf 'Building and installing Nahj Desktop.\n'
./package.sh
cd dist
if makepkg --install --force; then
    :
else
    status=$?
    printf '\nPackage installation stopped (exit %s). Resolve the error above, then rerun this installer.\n' "$status" >&2
    exit "$status"
fi
nahj-desktop --check
printf '\nNahj is installed. Open it from the application menu or run nahj-desktop.\n'
