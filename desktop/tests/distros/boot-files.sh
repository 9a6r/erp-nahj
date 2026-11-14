#!/usr/bin/env bash
# Inside a disposable derivative root/VM only. No bootloader is installed.
set -euo pipefail
test -e /etc/nahj-disposable-compatibility
wanted=${1:-any}
kernel=
for directory in /usr/lib/modules/*; do
    [[ -f "$directory/pkgbase" ]] || continue
    pkgbase=$(cat "$directory/pkgbase")
    if [[ "$wanted" == any || "$pkgbase" == "$wanted" ]]; then
        kernel=${directory##*/}
        break
    fi
done
test -n "$kernel"
if [[ -f /usr/lib/modules/$kernel/vmlinuz ]]; then
    cp "/usr/lib/modules/$kernel/vmlinuz" /tmp/nahj-vmlinuz
elif [[ -f /boot/vmlinuz-$pkgbase ]]; then
    cp "/boot/vmlinuz-$pkgbase" /tmp/nahj-vmlinuz
else
    echo "No kernel image for $kernel ($pkgbase)" >&2
    exit 1
fi
# Build a normal disk-root initramfs, not the ISO's live/squashfs boot path.
# This is VM provisioning; it does not alter the distro's normal boot config.
if command -v dracut >/dev/null; then
    mkdir -p /tmp/nahj-empty-dracut
    dracut --force --no-hostonly --no-hostonly-cmdline --no-uefi \
        --conf /dev/null --confdir /tmp/nahj-empty-dracut \
        --omit 'dmsquash-live dmsquash-live-autooverlay' \
        --add-drivers 'virtio_pci virtio_blk virtio_net ext4' \
        --filesystems ext4 --kver "$kernel" /tmp/nahj-initramfs.img
else
    cat > /tmp/nahj-mkinitcpio.conf <<'EOF'
MODULES=(virtio_pci virtio_blk virtio_net ext4)
BINARIES=()
FILES=()
HOOKS=(base udev modconf block filesystems fsck)
COMPRESSION="zstd"
EOF
    mkinitcpio -c /tmp/nahj-mkinitcpio.conf -k "$kernel" -g /tmp/nahj-initramfs.img
fi
printf 'Kernel prepared: %s (%s)\n' "$kernel" "$pkgbase"
