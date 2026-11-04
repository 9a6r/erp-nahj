import threading
import shutil
import ssl
import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from nahj_desktop.connection import probe, ConnectionFailure

class Handler(BaseHTTPRequestHandler):
    mode = 'ok'
    def do_GET(self):
        if self.mode == 'access':
            self.send_response(403); self.end_headers(); return
        if self.mode == 'redirect':
            self.send_response(302); self.send_header('Location', 'https://example.invalid'); self.end_headers(); return
        self.send_response(200); self.end_headers()
        values = {'ok': b'{"message":"pong"}', 'invalid': b'<html>Login</html>', 'large': b'x' * 65537, 'array': b'[]'}
        self.wfile.write(values[self.mode])
    def log_message(self, *_): pass

class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def test_real_frappe_response(self):
        Handler.mode = 'ok'
        self.assertEqual(probe(self.origin), self.origin)

    def test_rejects_invalid_servers_and_redirects(self):
        for mode, code in [('access','access'),('redirect','redirect'),('invalid','invalid'),('large','invalid'),('array','invalid')]:
            with self.subTest(mode=mode):
                Handler.mode = mode
                with self.assertRaises(ConnectionFailure) as error:
                    probe(self.origin)
                self.assertEqual(str(error.exception), code)


@unittest.skipUnless(shutil.which('openssl'), 'OpenSSL is required for real TLS verification tests')
class TLSConnectionTests(unittest.TestCase):
    def test_trusted_tls_works_and_untrusted_or_wrong_hostname_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            certificate, key = root / 'certificate.pem', root / 'key.pem'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-sha256', '-nodes',
                            '-days', '1', '-subj', '/CN=localhost',
                            '-addext', 'subjectAltName=DNS:localhost',
                            '-addext', 'basicConstraints=critical,CA:TRUE',
                            '-addext', 'keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign',
                            '-keyout', str(key), '-out', str(certificate)],
                           check=True, capture_output=True)
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.load_cert_chain(certificate, key)
            server.socket = tls.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            Handler.mode = 'ok'
            origin = f'https://localhost:{server.server_port}'
            try:
                with self.assertRaises(ConnectionFailure) as error:
                    probe(origin)
                self.assertEqual(str(error.exception), 'tls')
                trusted = ssl.create_default_context(cafile=str(certificate))
                # A test-only trust root, with normal certificate and hostname
                # verification. Production uses the operating system trust store.
                with patch('ssl._create_default_https_context', return_value=trusted):
                    self.assertEqual(probe(origin), origin)
                    with self.assertRaises(ConnectionFailure) as error:
                        probe(f'https://127.0.0.1:{server.server_port}')
                    self.assertEqual(str(error.exception), 'tls')
                self.assertTrue(trusted.check_hostname)
                self.assertEqual(trusted.verify_mode, ssl.CERT_REQUIRED)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
