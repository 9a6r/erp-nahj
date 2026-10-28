import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nahj_desktop.server import Server, ServerError, compose_spec, private_write, validate


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.server = Server(self.root / 'state')
        self.profile = dict(mode='local', site='nahj.localhost', port=8088,
                            project='nahj-test', image='sha256:123', initialized=True)
        private_write(self.server.root / 'profile.json', json.dumps(self.profile))

    def test_stop_retains_volumes(self):
        with patch.object(self.server, 'compose') as command:
            self.server.stop()
        command.assert_called_once_with('stop', '--timeout', '60')
        self.assertTrue((self.server.root / 'profile.json').exists())

    def test_backend_uses_labels_not_container_names(self):
        with patch.object(self.server, 'run', return_value='ab123\n') as command:
            self.assertEqual(self.server.backend(), 'ab123')
        args = command.call_args.args[0]
        self.assertIn('label=io.nahj.project=nahj-test', args)
        self.assertIn('label=io.nahj.service=backend', args)
        with patch.object(self.server, 'run', return_value='a\nb\n'):
            with self.assertRaises(ServerError):
                self.server.backend()

    def test_bad_checksum_never_imported(self):
        image = self.root / 'bad.tar.gz'
        image.write_bytes(b'not the release')
        with patch.object(self.server, 'run') as command:
            with self.assertRaisesRegex(ServerError, 'checksum'):
                self.server.import_image(image)
        command.assert_not_called()

    def test_concurrent_operations_are_refused(self):
        other = Server(self.server.root)
        with self.server.locked():
            with self.assertRaises(ServerError):
                with other.locked():
                    self.fail('lock was not enforced')

    def test_compose_persists_data_and_binds_loopback(self):
        spec = compose_spec(self.profile, self.server.root)
        self.assertEqual(spec['services']['frontend']['ports'], ['127.0.0.1:8088:8080'])
        self.assertEqual(spec['services']['frontend']['environment']['PROXY_READ_TIMEOUT'], '300')
        self.assertIn('database:/var/lib/mysql', spec['services']['db']['volumes'])
        external = compose_spec({**self.profile, 'mode': 'external'}, self.server.root)
        self.assertNotIn('db', external['services'])
        self.assertTrue(any('/run/nahj/database-ca.pem:ro' in v for v in external['services']['backend']['volumes']))

    def test_config_and_backup_are_private(self):
        self.assertEqual((self.server.root / 'profile.json').stat().st_mode & 0o777, 0o600)
        def execute(args, **kwargs):
            if args[1] == 'cp':
                destination = Path(args[-1])
                if destination.is_dir():
                    for name in ('test-database.sql.gz', 'test-files.tgz', 'test-private-files.tgz', 'test-site_config_backup.json'):
                        (destination / name).write_bytes(b'backup bytes')
                else:
                    destination.write_text('{}')
            return ''
        with patch.object(self.server, 'backend', return_value='backend-id'), patch.object(self.server, 'run', side_effect=execute):
            result = self.server.backup(self.root)
        manifest = json.loads((result / 'manifest.json').read_text())
        self.assertEqual(len(manifest['sha256']), 5)
        for file in result.iterdir():
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)

    def test_incomplete_backup_is_not_exported(self):
        with patch.object(self.server, 'backend', return_value='backend-id'), patch.object(self.server, 'run', return_value=''):
            with self.assertRaisesRegex(ServerError, 'Incomplete'):
                self.server.backup(self.root)
        self.assertEqual(list(self.root.glob('*backup*')), [])

    def test_invalid_configuration_rejected(self):
        for options in (dict(mode='local', site='../escape'), dict(mode='local', site='site', port=0),
                        dict(mode='external', site='site', db_host='db', db_user='user', db_name='db', ca='')):
            with self.subTest(options=options), self.assertRaises(ServerError):
                validate(options)

    def test_existing_site_never_overwritten(self):
        with patch.object(self.server, 'run') as command:
            with self.assertRaisesRegex(ServerError, 'already configured'):
                self.server.setup(self.profile, '/unused', 'a-long-test-password')
        command.assert_not_called()

    def test_resume_keeps_identity_and_uses_stdin_for_credentials(self):
        private_write(self.server.root / 'profile.json', json.dumps({**self.profile, 'initialized': False}))
        private_write(self.server.root / 'db-password', 'private-test-password')
        with patch.object(self.server, 'compose') as command, patch.object(self.server, '_start', return_value='ready'):
            self.assertEqual(self.server.resume('private-admin-password'), 'ready')
        saved = self.server.profile()
        self.assertTrue(saved['initialized'])
        self.assertEqual(saved['project'], self.profile['project'])
        self.assertNotIn('password', saved)
        run = command.call_args
        self.assertNotIn('private-test-password', str(run.args))
        self.assertEqual(json.loads(run.kwargs['payload'])['password'], 'private-test-password')


if __name__ == '__main__':
    unittest.main()
