"""Run with dbus-run-session -- xvfb-run -a python3 tests/smoke_gui.py."""
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from nahj_desktop.app import Nahj, GLib, WebKit
from nahj_desktop import config

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json' if self.path.startswith('/api/') else 'text/html')
        self.end_headers()
        self.wfile.write(b'{"message":"pong"}' if self.path.startswith('/api/') else b'<html><title>Nahj smoke</title><body>Connected</body></html>')
    def log_message(self, *_): pass

with tempfile.TemporaryDirectory() as root:
    os.environ['XDG_CONFIG_HOME'] = root
    os.environ['XDG_DATA_HOME'] = root
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    app = Nahj()
    result = {'passed': False}
    def begin(*_):
        app.address.set_text(f'http://127.0.0.1:{server.server_port}')
        app.language.set_selected(1)
        assert app.settings['language'] == 'en'
        app.connect_server()
        GLib.timeout_add(100, inspect)
    def inspect():
        if app.web and app.web.get_title() == 'Nahj smoke':
            assert config.load()['server'].endswith(str(server.server_port))
            app.show_settings()
            app.navigate('/app')
            result['passed'] = True
            app.quit()
            return False
        return True
    app.connect('activate', begin)
    GLib.timeout_add_seconds(25, lambda: (app.quit(), False)[1])
    app.run([])
    server.shutdown()
    assert result['passed'], 'Native WebKit page did not finish loading'
    print('PASS: native window, language switch, server probe, saved settings, WebKit load and navigation')
