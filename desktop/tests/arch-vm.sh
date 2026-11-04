#!/usr/bin/env bash
# Disposable Ubuntu CI host only. Tests an actual Arch guest and Zen kernel.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
work=${RUNNER_TEMP:?Run this script on a disposable CI runner}/nahj-arch
mkdir -p "$work/results"
cd "$work"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends qemu-system-x86 qemu-utils cloud-image-utils
image=Arch-Linux-x86_64-cloudimg-20261101.620452.qcow2
base=https://fastly.mirror.pkgbuild.com/images/v20261101.620452
curl --fail --location --retry 3 -o "$image" "$base/$image"
curl --fail --location --retry 3 -o "$image.SHA256" "$base/$image.SHA256"
sha256sum --check "$image.SHA256" | tee results/image-checksum.txt
cp "$image.SHA256" results/
qemu-img resize "$image" 24G
ssh-keygen -q -t ed25519 -N '' -f test-key
cat > user-data <<EOF
#cloud-config
users:
  - name: nahj
    groups: [wheel]
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: true
    ssh_authorized_keys:
      - $(cat test-key.pub)
ssh_pwauth: false
disable_root: true
EOF
printf 'instance-id: nahj-arch-test\nlocal-hostname: nahj-arch-test\n' > meta-data
cloud-localds seed.img user-data meta-data
ssh_options=(-i "$work/test-key" -p 22222 -o BatchMode=yes -o ConnectTimeout=5
             -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$work/known_hosts")
remote() { ssh "${ssh_options[@]}" nahj@127.0.0.1 "$@"; }
copy_to_guest() { scp -q -i "$work/test-key" -P 22222 -o BatchMode=yes -o UserKnownHostsFile="$work/known_hosts" "$1" "nahj@127.0.0.1:$2"; }
vm_pid=
stop_vm() {
    if [[ -n "$vm_pid" ]] && kill -0 "$vm_pid" 2>/dev/null; then
        remote sudo poweroff || true
        for _ in {1..30}; do kill -0 "$vm_pid" 2>/dev/null || break; sleep 1; done
        kill "$vm_pid" 2>/dev/null || true
        wait "$vm_pid" 2>/dev/null || true
    fi
    vm_pid=
}
trap stop_vm EXIT
boot() {
    accel=(-accel tcg,thread=multi -cpu max)
    if [[ -r /dev/kvm && -w /dev/kvm ]]; then accel=(-accel kvm -cpu host); fi
    qemu-system-x86_64 "${accel[@]}" -m 4096 -smp 2 -display none -monitor none \
        -serial "file:$work/results/serial.log" \
        -drive "file=$work/$image,if=virtio,format=qcow2" \
        -drive "file=$work/seed.img,if=virtio,format=raw" \
        -netdev user,id=net0,hostfwd=tcp:127.0.0.1:22222-:22 -device virtio-net-pci,netdev=net0 "$@" &
    vm_pid=$!
    for _ in {1..120}; do
        if remote true 2>/dev/null; then return; fi
        kill -0 "$vm_pid"
        sleep 5
    done
    echo 'Arch guest did not become ready' >&2
    return 1
}
boot
remote 'sudo cloud-init status --wait'
remote 'sudo pacman -Syu --noconfirm --needed linux-zen base-devel python python-gobject gtk4 webkitgtk-6.0 gst-plugins-good noto-fonts adwaita-icon-theme podman podman-compose slirp4netns fuse-overlayfs xorg-server-xvfb xorg-xauth dbus openbox xdotool weston' | tee results/packages.log
# Boot the kernel we just installed explicitly; do not depend on bootloader order.
remote 'sudo cat /boot/vmlinuz-linux-zen' > vmlinuz-linux-zen
remote 'sudo cat /boot/initramfs-linux-zen.img' > initramfs-linux-zen.img
root_uuid=$(remote 'findmnt -no UUID /')
[[ "$root_uuid" =~ ^[a-fA-F0-9-]+$ ]]
stop_vm
boot -kernel "$work/vmlinuz-linux-zen" -initrd "$work/initramfs-linux-zen.img" -append "root=UUID=$root_uuid rw console=ttyS0"
remote 'uname -r | tee kernel.txt; uname -r | grep -q zen'
tar --exclude=desktop/dist --exclude=__pycache__ --exclude=desktop/screenshots -C "$repo" -czf desktop-test.tar.gz desktop license.txt
copy_to_guest desktop-test.tar.gz /home/nahj/desktop-test.tar.gz
remote 'mkdir -p source; tar -xzf desktop-test.tar.gz -C source; bash source/desktop/tests/arch-guest.sh' | tee results/native-tests.log
stop_vm
boot -kernel "$work/vmlinuz-linux-zen" -initrd "$work/initramfs-linux-zen.img" -append "root=UUID=$root_uuid rw console=ttyS0"
remote 'podman start nahj-arch-persistence; test "$(podman exec nahj-arch-persistence redis-cli GET nahj-persistence)" = survives-reboot; podman stop nahj-arch-persistence; echo "PASS: rootless volume data survived a full Zen VM reboot"' | tee results/reboot.log
remote 'uname -a; pacman -Q linux-zen python gtk4 webkitgtk-6.0 podman podman-compose; podman info --format "rootless={{.Host.Security.Rootless}} storage={{.Store.GraphDriverName}}"' > results/environment.txt
