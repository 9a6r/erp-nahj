import threading
import unittest
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
