#!/usr/bin/env bash
# Sourced by arch-vm.sh on an ephemeral GitHub runner, never a user's OS.
[[ ${GITHUB_ACTIONS:-} == true && ${RUNNER_OS:-} == Linux ]]
[[ "$work" == "$RUNNER_TEMP/nahj-arch" && ! -e "$work/rootfs" && ! -e "$work/distro.img" ]]
case "$NAHJ_DISTRO" in endeavouros|garuda) ;; *) exit 2;; esac
sudo apt-get install -y --no-install-recommends libarchive-tools squashfs-tools e2fsprogs
python3 - "$repo" "$NAHJ_DISTRO" <<'PY'
import hashlib,json,re,subprocess,sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen
r=json.loads(Path(sys.argv[1],'desktop/tests/distros/images.json').read_text())[sys.argv[2]]
if 'checksum_url' in r:
    with urlopen(r['checksum_url'],timeout=60) as response: checksum=response.read().decode()
    Path('results/vendor-checksum.txt').write_text(checksum)
    match=re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?([^\s]+)\s*',checksum)
    assert match and match[2]==Path(urlsplit(r['url']).path).name
    r['digest']=match[1].lower()
subprocess.run(['curl','--fail','--location','--retry','3','--max-time','1200','-o','vendor.iso',r['url']],check=True)
with Path('vendor.iso').open('rb') as f: actual=hashlib.file_digest(f,r['algorithm']).hexdigest()
assert actual==r['digest'], 'Vendor ISO checksum mismatch'
r['size']=Path('vendor.iso').stat().st_size
Path('results/iso-provenance.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS: official ISO checksum verified:',sys.argv[2],actual)
PY
bsdtar -tf vendor.iso > results/iso-files.txt
mapfile -t squash_paths < <(grep -E '(^|/)airootfs\.sfs$' results/iso-files.txt)
[[ ${#squash_paths[@]} == 1 ]]
bsdtar -xOf vendor.iso "${squash_paths[0]}" > airootfs.sfs
rm vendor.iso
sudo unsquashfs -no-progress -d "$work/rootfs" airootfs.sfs
rm airootfs.sfs
sudo cp rootfs/etc/os-release results/iso-os-release.txt
sudo cp rootfs/etc/pacman.conf results/iso-pacman.conf
sudo touch rootfs/etc/nahj-disposable-compatibility
sudo cp "$repo/desktop/tests/distros/boot-files.sh" rootfs/tmp/nahj-boot-files.sh
# Keep distro packages, repositories and identity intact. Replace only live
# session/network bootstrap with a locked-down disposable SSH test account.
sudo chroot rootfs /usr/bin/useradd -m -G wheel -s /bin/bash nahj
sudo chroot rootfs /usr/bin/passwd -d nahj
uid=$(sudo chroot rootfs id -u nahj)
gid=$(sudo chroot rootfs id -g nahj)
sudo install -d -m 700 -o "$uid" -g "$gid" rootfs/home/nahj/.ssh
sudo install -m 600 test-key.pub rootfs/home/nahj/.ssh/authorized_keys
sudo chown -R "$uid:$gid" rootfs/home/nahj/.ssh
sudo chroot rootfs /usr/bin/ssh-keygen -A
printf 'nahj ALL=(ALL) NOPASSWD: ALL\n' | sudo tee rootfs/etc/sudoers.d/nahj-ci >/dev/null
sudo chmod 440 rootfs/etc/sudoers.d/nahj-ci
sudo mkdir -p rootfs/etc/ssh/sshd_config.d rootfs/etc/systemd/network
printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\nAllowUsers nahj\n' | sudo tee rootfs/etc/ssh/sshd_config.d/00-nahj-ci.conf >/dev/null
printf '[Match]\nName=eth0\n[Network]\nDHCP=yes\n' | sudo tee rootfs/etc/systemd/network/00-nahj-ci.network >/dev/null
sudo systemctl --root="$work/rootfs" set-default multi-user.target
sudo systemctl --root="$work/rootfs" disable NetworkManager.service 2>/dev/null || true
sudo systemctl --root="$work/rootfs" enable sshd.service systemd-networkd.service systemd-resolved.service
sudo ln -sf /run/systemd/resolve/stub-resolv.conf rootfs/etc/resolv.conf
sudo truncate -s 0 rootfs/etc/fstab
# Device and proc mounts exist only for initramfs generation and are unmounted
# before packing. The host's /sys is read-only; no distro installer is invoked.
trap 'sudo umount "$work/rootfs/sys" "$work/rootfs/proc" "$work/rootfs/dev" 2>/dev/null || true' EXIT
sudo mount --bind /dev rootfs/dev
sudo mount -t proc proc rootfs/proc
sudo mount --bind /sys rootfs/sys
sudo mount -o remount,bind,ro rootfs/sys
if sudo chroot rootfs /bin/bash /tmp/nahj-boot-files.sh any > results/bootstrap-initramfs.log 2>&1; then
    bootstrap_status=0
else
    bootstrap_status=$?
fi
sudo umount rootfs/sys rootfs/proc rootfs/dev
trap - EXIT
cat results/bootstrap-initramfs.log
[[ $bootstrap_status == 0 ]]
sudo cp rootfs/tmp/nahj-vmlinuz bootstrap-vmlinuz
sudo cp rootfs/tmp/nahj-initramfs.img bootstrap-initramfs.img
sudo chmod a+r bootstrap-vmlinuz bootstrap-initramfs.img
image=distro.img
image_format=raw
truncate -s 40G "$image"
sudo mkfs.ext4 -q -F -d "$work/rootfs" "$image"
sudo rm -rf -- "$work/rootfs"
root_uuid=$(sudo blkid -s UUID -o value "$image")
[[ "$root_uuid" =~ ^[a-fA-F0-9-]+$ ]]
initial_boot=(-kernel "$work/bootstrap-vmlinuz" -initrd "$work/bootstrap-initramfs.img" -append "root=UUID=$root_uuid rw console=ttyS0 net.ifnames=0")
seed_drive=()
