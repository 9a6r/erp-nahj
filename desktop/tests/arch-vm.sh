#!/usr/bin/env bash
# Disposable Ubuntu CI host only. Tests an actual Arch guest and Zen kernel.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
work=${RUNNER_TEMP:?Run this script on a disposable CI runner}/nahj-arch
mkdir -p "$work/results"
cd "$work"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends qemu-system-x86 qemu-utils cloud-image-utils acl
# Only this disposable CI runner: use hardware acceleration when it is exposed.
if [[ -e /dev/kvm ]]; then sudo setfacl -m "u:$(id -un):rw" /dev/kvm; fi
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
boot_number=0
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
    boot_number=$((boot_number + 1))
    if [[ -e /dev/kvm ]]; then sudo setfacl -m "u:$(id -un):rw" /dev/kvm; fi
    accel=(-accel tcg,thread=multi -cpu max)
    if [[ -r /dev/kvm && -w /dev/kvm ]]; then accel=(-accel kvm -cpu host); fi
    echo "Boot $boot_number using ${accel[*]}" | tee -a results/boots.log
    memory=4096
    if [[ ${NAHJ_FULL_STACK:-0} == 1 ]]; then memory=5632; fi
    qemu-system-x86_64 "${accel[@]}" -m "$memory" -smp 2 -display none -monitor none \
        -serial "file:$work/results/serial-$boot_number.log" \
        -drive "file=$work/$image,if=virtio,format=qcow2" \
        -drive "file=$work/seed.img,if=virtio,format=raw" \
        -netdev user,id=net0,hostfwd=tcp:127.0.0.1:22222-:22 -device virtio-net-pci,netdev=net0 "$@" &
    vm_pid=$!
    for attempt in {1..120}; do
        if remote true 2>results/last-ssh-error.log; then return; fi
        kill -0 "$vm_pid"
        if (( attempt % 6 == 0 )); then
            echo "Waiting for SSH on boot $boot_number, attempt $attempt/120"
            tail -n 3 "results/serial-$boot_number.log"
        fi
        sleep 5
    done
    echo 'Arch guest did not become ready' >&2
    cat results/last-ssh-error.log >&2
    tail -n 80 "results/serial-$boot_number.log" >&2
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
# The cloud image configures eth0; retain its interface naming when bypassing
# its bootloader, otherwise the Zen boot renames the device ens3 and loses DHCP.
zen_cmdline="root=UUID=$root_uuid rw console=ttyS0 net.ifnames=0"
boot -kernel "$work/vmlinuz-linux-zen" -initrd "$work/initramfs-linux-zen.img" -append "$zen_cmdline"
remote 'uname -r | tee kernel.txt; uname -r | grep -q zen'
tar --exclude=desktop/dist --exclude=__pycache__ --exclude=desktop/screenshots -C "$repo" -czf desktop-test.tar.gz desktop license.txt
copy_to_guest desktop-test.tar.gz /home/nahj/desktop-test.tar.gz
remote 'set -e; mkdir -p source; tar -xzf desktop-test.tar.gz -C source'
if [[ ${NAHJ_FULL_STACK:-0} == 1 ]]; then
    copy_to_guest "$RUNNER_TEMP/nahj-build/nahj-server-0.3.1-rc1-amd64.tar.gz" /home/nahj/server.tar.gz
    remote 'cd source/desktop; PYTHONPATH=. python tests/full_stack.py prepare' 2>&1 | tee results/full-stack.log
else
    remote 'bash source/desktop/tests/arch-guest.sh' 2>&1 | tee results/native-tests.log
fi
stop_vm
boot -kernel "$work/vmlinuz-linux-zen" -initrd "$work/initramfs-linux-zen.img" -append "$zen_cmdline"
if [[ ${NAHJ_FULL_STACK:-0} == 1 ]]; then
    remote 'cd source/desktop; PYTHONPATH=. python tests/full_stack.py after-reboot' 2>&1 | tee results/full-stack-reboot.log
else
    remote 'set -e; podman start nahj-arch-persistence; test "$(podman exec nahj-arch-persistence redis-cli GET nahj-persistence)" = survives-reboot; podman stop nahj-arch-persistence; echo "PASS: rootless volume data survived a full Zen VM reboot"' 2>&1 | tee results/reboot.log
fi
remote 'uname -a; pacman -Q linux-zen python gtk4 webkitgtk-6.0 podman podman-compose; podman info --format "rootless={{.Host.Security.Rootless}} storage={{.Store.GraphDriverName}}"' > results/environment.txt
