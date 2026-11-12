import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from nahj_desktop.backup import BackupError, extract_attachments, inspect_backup
from nahj_desktop.server import IMAGE_ID, Server, ServerError, private_write


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'backup'
        self.source.mkdir()
        (self.source / 'test-database.sql.gz').write_bytes(gzip.compress(b'-- fixture'))
        (self.source / 'test-site_config_backup.json').write_text('{"db_type":"mariadb"}')
        self.archive('public', 'original.localhost/public/files/فاتورة.txt')
        self.archive('private', 'original.localhost/private/files/secret.txt')
        self.manifest()

    def archive(self, visibility, name, kind=tarfile.REGTYPE):
        filename = 'test-files.tgz' if visibility == 'public' else 'test-private-files.tgz'
        with tarfile.open(self.source / filename, 'w:gz') as archive:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = 7 if kind == tarfile.REGTYPE else 0
            member.linkname = '/tmp/outside' if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ''
            archive.addfile(member, io.BytesIO(b'content') if member.isfile() else None)

    def manifest(self, **changes):
        data = {'format': 1, 'image': IMAGE_ID, 'site': 'original.localhost', 'sha256': {
            file.name: hashlib.sha256(file.read_bytes()).hexdigest()
            for file in self.source.iterdir() if file.name != 'manifest.json'}}
        data.update(changes)
        (self.source / 'manifest.json').write_text(json.dumps(data))

    def test_extracts_both_attachment_classes_without_overwriting(self):
        report = inspect_backup(self.source, IMAGE_ID)
        destination = self.root / 'new-site'
        extract_attachments(self.source, destination, report)
        self.assertEqual((destination / 'public/files/فاتورة.txt').read_bytes(), b'content')
        private = destination / 'private/files/secret.txt'
        self.assertEqual(private.read_bytes(), b'content')
        self.assertEqual(private.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            extract_attachments(self.source, destination, report)

    def test_damage_extra_files_and_wrong_image_are_rejected(self):
        (self.source / 'test-database.sql.gz').write_bytes(b'damaged')
        with self.assertRaisesRegex(BackupError, 'checksum mismatch'):
            inspect_backup(self.source, IMAGE_ID)
        self.manifest(image='sha256:another-release')
        with self.assertRaisesRegex(BackupError, 'server image'):
            inspect_backup(self.source, IMAGE_ID)
        self.manifest()
        (self.source / 'unexpected').write_text('extra')
        with self.assertRaisesRegex(BackupError, 'differ'):
            inspect_backup(self.source, IMAGE_ID)

    def test_cross_image_restore_requires_explicit_source_and_matching_versions(self):
        old = 'sha256:' + 'a' * 64
        self.manifest(image=old)
        path = self.source / 'manifest.json'
        data = json.loads(path.read_text())
        versions = {'erpnext_version': '16.53.0', 'frappe_version': '16.54.0'}
        with self.assertRaisesRegex(BackupError, 'versions'):
            inspect_backup(self.source, IMAGE_ID, {old: versions})
        data.update(versions)
        path.write_text(json.dumps(data))
        self.assertEqual(inspect_backup(self.source, IMAGE_ID, {old: versions})['manifest']['image'], old)
        data['erpnext_version'] = '17.0.0'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(BackupError, 'versions'):
            inspect_backup(self.source, IMAGE_ID, {old: versions})
        with self.assertRaisesRegex(BackupError, 'server image'):
            inspect_backup(self.source, IMAGE_ID)

    def test_rejects_traversal_links_devices_and_cross_visibility(self):
        for name, kind in [
            ('original.localhost/public/files/../../escape', tarfile.REGTYPE),
            ('/original.localhost/public/files/escape', tarfile.REGTYPE),
            ('original.localhost/private/files/escape', tarfile.REGTYPE),
            ('original.localhost/public/files/link', tarfile.SYMTYPE),
            ('original.localhost/public/files/link', tarfile.LNKTYPE),
            ('original.localhost/public/files/device', tarfile.CHRTYPE),
        ]:
            with self.subTest(name=name, kind=kind):
                self.archive('public', name, kind)
                self.manifest()
                with self.assertRaisesRegex(BackupError, 'Unsafe'):
                    inspect_backup(self.source, IMAGE_ID)

    def test_symlinked_backup_and_untrusted_filenames_are_rejected(self):
        file = self.source / 'test-database.sql.gz'
        file.rename(self.root / 'elsewhere')
        file.symlink_to(self.root / 'elsewhere')
        with self.assertRaisesRegex(BackupError, 'symbolic links'):
            inspect_backup(self.source, IMAGE_ID)
        file.unlink()
        (self.root / 'elsewhere').rename(self.source / 'bad;command-database.sql.gz')
        self.manifest()
        with self.assertRaisesRegex(BackupError, 'checksum manifest'):
            inspect_backup(self.source, IMAGE_ID)

    def test_restore_never_overwrites_an_existing_profile_or_resumes_failed_restore(self):
        server = Server(self.root / 'state')
        options = {'site': 'new.localhost', 'mode': 'local', 'port': 8088}
        saved = {**options, 'image': IMAGE_ID, 'operation': 'restore', 'initialized': False}
        private_write(server.root / 'profile.json', json.dumps(saved))
        with patch.object(server, 'run') as command:
            with self.assertRaisesRegex(ServerError, 'already configured'):
                server.restore(self.source, options)
            with self.assertRaisesRegex(ServerError, 'Recovery did not complete'):
                server.resume()
        command.assert_not_called()

    def test_failed_recovery_cannot_be_marked_initialized(self):
        server = Server(self.root / 'state')
        options = {'site': 'new.localhost', 'mode': 'local', 'port': 8088}
        with patch.object(server, 'run', return_value='true'), patch.object(server, 'import_image', return_value=IMAGE_ID), \
             patch.object(server, 'compose', side_effect=[None, ServerError('restore failed')]):
            with self.assertRaisesRegex(ServerError, 'restore failed'):
                server.restore(self.source, options, '/verified-image')
        self.assertFalse(server.profile()['initialized'])
        self.assertEqual(server.profile()['operation'], 'restore')
        self.assertFalse((server.root / 'recovery-input').exists())

    def test_recovery_starts_only_review_services(self):
        server = Server(self.root / 'state')
        options = dict(site='new.localhost', mode='local', port=8088, image=IMAGE_ID,
                       initialized=True, recovery_pending=True)
        private_write(server.root / 'profile.json', json.dumps(options))
        with patch.object(server, 'compose') as command, patch('nahj_desktop.server.probe'):
            server.start()
        services = command.call_args.args
        self.assertIn('backend', services)
        self.assertNotIn('scheduler', services)
        self.assertNotIn('worker', services)


if __name__ == '__main__':
    unittest.main()
