import unittest

from nahj_desktop.server_messages import translate_error


class ServerMessageTests(unittest.TestCase):
    def test_helper_error_inside_command_traceback_keeps_diagnostics(self):
        trace = ('Command failed (1): Traceback (most recent call last):\n'
                 '  File "/tmp/restore.py", line 42, in main\n'
                 'RuntimeError: External database is not empty; provisioning refused.\n')
        translated = translate_error(trace)
        self.assertTrue(translated.startswith('فشل الأمر (1): Traceback'))
        self.assertIn('File "/tmp/restore.py", line 42, in main', translated)
        self.assertIn('RuntimeError: قاعدة البيانات الخارجية ليست فارغة', translated)
        self.assertNotIn('External database is not empty', translated)
        self.assertTrue(translated.endswith('\n'))

    def test_inline_exception_and_unknown_diagnostics(self):
        self.assertEqual(translate_error('Command failed (-9): RuntimeError: MariaDB TLS is required.'),
                         'فشل الأمر (-9): RuntimeError: يلزم اتصال مشفّر عبر TLS مع MariaDB.')
        unknown = 'pymysql.err.OperationalError: (1045, "Access denied for test_user")'
        self.assertEqual(translate_error(unknown), unknown)
        path = '/backups/External database is not empty; provisioning refused./manifest.json'
        self.assertEqual(translate_error(path), path)


if __name__ == '__main__':
    unittest.main()
