# Arch derivative / Zen acceptance

This matrix boots separate EndeavourOS and Garuda filesystems from the official
ISO releases in `images.json`. It does not relabel an Arch cloud image. ISO
checksums are verified before extraction; source URLs, hashes, `/etc/os-release`,
repository configuration and installed packages are retained as evidence.

Only disposable GitHub runners may prepare the images. The harness replaces the
live session's network/login bootstrap with a test SSH account, creates a
persistent ext4 VM disk, and builds a disk-root initramfs. It retains the distro's
packages, settings, package signatures and repositories. It updates the disposable
system, installs `linux-zen`, explicitly boots that kernel, and checks `uname -r`.
Garuda's Temeraire release defaults to `linux-garuda`; testing its default kernel
would not establish the requested Zen compatibility.

Each VM runs the actual Nahj installer, native X11/Weston checks, Arabic/English,
downloads, package lifecycle and rootless Podman checks. The same VM then runs
the published ERP server, actual business transactions, backup/independent
restore and a complete Zen reboot. A failing bootstrap or application check is
a failed result, never a successful compatibility claim.

This validates the application's runtime on an ISO-derived installed filesystem.
It does not test Calamares, the distro's bootloader installation, the full themed
KDE/Hyprland session, encrypted/Btrfs layouts or physical GPU drivers. The ext4
test disk is a deliberate fixture; in particular it is not Garuda's default
Btrfs/snapshot layout. Successful results must state that scope.

Nahj Linux's `distro/README.md` specifies Arch, Zen and Hyprland/Vitreus. Its
repository had no published ISO release on 2026-11-14. Its exact custom session
therefore remains separate from successful generic Arch/Zen evidence.
