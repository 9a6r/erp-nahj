"""Exercise installer failure boundaries without changing system packages."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipIf(os.geteuid() == 0, 'The installer requires an ordinary user')
class InstallerTests(unittest.TestCase):
    def run_installer(self, missing='', pacman_status=0, build_status=0):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy(Path(__file__).resolve().parents[1] / 'install.sh', root)
            commands = root / 'bin'
            commands.mkdir()
            fake = '''#!/bin/bash
name=${0##*/}
printf '%s %s\\n' "$name" "$*" >> "$INSTALL_LOG"
case "$name" in
    pacman)
        if [[ $1 == -Q ]]; then [[ $2 != "$MISSING_PACKAGE" ]]; exit $?; fi
        exit "$PACMAN_STATUS" ;;
    sudo) exec "$@" ;;
    makepkg) exit "$BUILD_STATUS" ;;
    nahj-desktop) exit 0 ;;
esac
'''
            for name in ('pacman', 'sudo', 'makepkg', 'nahj-desktop'):
                path = commands / name
                path.write_text(fake)
                path.chmod(0o755)
            package = root / 'package.sh'
            package.write_text('#!/bin/bash\nprintf "package\\n" >> "$INSTALL_LOG"\nmkdir -p dist\n')
            package.chmod(0o755)
            log = root / 'calls'
            env = dict(os.environ, PATH=f'{commands}:/usr/bin:/bin', INSTALL_LOG=str(log),
                       MISSING_PACKAGE=missing, PACMAN_STATUS=str(pacman_status),
                       BUILD_STATUS=str(build_status))
            result = subprocess.run(['bash', str(root / 'install.sh')], env=env,
                                    capture_output=True, text=True)
            return result, log.read_text()

    def test_existing_dependencies_do_not_start_package_transaction(self):
        result, calls = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('sudo ', calls)
        self.assertIn('nahj-desktop --check', calls)
        # Rebuilding a checkout must install its changes even at the same version.
        install = next(line for line in calls.splitlines() if line.startswith('makepkg '))
        self.assertNotIn('--needed', install)

    def test_installs_only_missing_dependency_without_refresh_or_upgrade(self):
        result, calls = self.run_installer(missing='python-gobject')
        self.assertEqual(result.returncode, 0, result.stderr)
        transactions = [line for line in calls.splitlines() if line.startswith('pacman -S')]
        self.assertEqual(transactions, ['pacman -S --needed python-gobject'])
        self.assertNotIn('--syncdeps', calls)

    def test_killed_dependency_install_does_not_build_or_claim_success(self):
        result, calls = self.run_installer(missing='python-gobject', pacman_status=137)
        self.assertEqual(result.returncode, 137)
        self.assertIn('killed', result.stderr)
        self.assertNotIn('package\n', calls)
        self.assertNotIn('makepkg ', calls)
        self.assertNotIn('Nahj is installed', result.stdout)

    def test_build_failure_does_not_claim_success(self):
        result, calls = self.run_installer(build_status=4)
        self.assertEqual(result.returncode, 4)
        self.assertNotIn('nahj-desktop --check', calls)
        self.assertNotIn('Nahj is installed', result.stdout)
