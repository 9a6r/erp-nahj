import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nahj_desktop import server_download as download
from nahj_desktop.server import ServerError


class Response(BytesIO):
    status = 206
    headers = {'Content-Range': 'bytes 3-5/6'}


class DownloadTests(unittest.TestCase):
    def setUp(self):
        published = patch.object(download, 'PUBLISHED', True)
        published.start()
        self.addCleanup(published.stop)

    def test_resume_verifies_complete_file(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            part = cache / (download.FILENAME + '.part')
            part.write_bytes(b'abc')
            with patch.object(download, 'SIZE', 6), patch.object(download, 'IMAGE_SHA256', hashlib.sha256(b'abcdef').hexdigest()), patch.object(download, 'urlopen', return_value=Response(b'def')) as request:
                result = download.download(lambda _: None, cache)
            self.assertEqual(result.read_bytes(), b'abcdef')
            self.assertEqual(request.call_args.args[0].get_header('Range'), 'bytes=3-')
            self.assertFalse(part.exists())

    def test_wrong_range_never_appended(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(download, 'SIZE', 6), patch.object(download, 'urlopen', return_value=Response(b'def')):
                with self.assertRaisesRegex(ServerError, 'byte range'):
                    download.download(lambda _: None, directory)

    def test_corrupt_cached_archive_never_used(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / download.FILENAME).write_bytes(b'bad')
            with patch.object(download, 'urlopen') as request:
                with self.assertRaises(ServerError):
                    download.download(lambda _: None, directory)
            request.assert_not_called()

    def test_unpublished_archive_does_not_attempt_a_dead_download(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(download, 'PUBLISHED', False), patch.object(download, 'urlopen') as request:
                with self.assertRaisesRegex(ServerError, 'under validation'):
                    download.download(lambda _: None, directory)
            request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
