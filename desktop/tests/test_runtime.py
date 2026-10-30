from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import threading
import unittest

from nahj_desktop.runtime import BridgeServer, PrintBridge, bridge_port


class RuntimeTests(unittest.TestCase):
    def test_private_print_request_reaches_the_frontend_unchanged(self):
        received = []

        class Frontend(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append((self.path, self.headers.get('Cookie')))
                self.send_response(200)
                self.end_headers()
                self.wfile.write('فاتورة نهج'.encode())

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(('127.0.0.1', 0), Frontend) as frontend:
            class Forwarder(PrintBridge):
                destination = frontend.server_address

            with BridgeServer(('127.0.0.1', 0), Forwarder) as bridge:
                threads = [threading.Thread(target=server.serve_forever) for server in (frontend, bridge)]
                for thread in threads:
                    thread.start()
                try:
                    with socket.create_connection(bridge.server_address) as client:
                        client.sendall(b'GET /private/files/print.png HTTP/1.0\r\nHost: 127.0.0.1\r\nCookie: sid=fixture\r\n\r\n')
                        content = b''
                        while chunk := client.recv(4096):
                            content += chunk
                    self.assertIn('فاتورة نهج'.encode(), content)
                    self.assertEqual(received, [('/private/files/print.png', 'sid=fixture')])
                    self.assertEqual(bridge.server_address[0], '127.0.0.1')
                finally:
                    bridge.shutdown()
                    frontend.shutdown()
                    for thread in threads:
                        thread.join()

    def test_renderer_port_cannot_target_an_external_origin_or_conflict_with_gunicorn(self):
        self.assertEqual(bridge_port({'host_name': 'http://127.0.0.1:8088'}), 8088)
        for url in ('https://example.com:8088', 'http://127.0.0.1:8000', 'http://127.0.0.1:80'):
            with self.subTest(url=url), self.assertRaises(RuntimeError):
                bridge_port({'host_name': url})
