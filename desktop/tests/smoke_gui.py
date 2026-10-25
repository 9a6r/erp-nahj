"""Native window, connection lifecycle and WebKit smoke test using a local server."""
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from nahj_desktop.app import Nahj, GLib
from nahj_desktop import config

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json' if self.path.startswith('/api/') else 'text/html')
        self.end_headers()
        self.wfile.write(b'{"message":"pong"}' if self.path.startswith('/api/') else b'<html><title>Nahj smoke</title><body>Connected<input id="draft" value="draft"></body></html>')
    def log_message(self, *_): pass

with tempfile.TemporaryDirectory() as root:
    os.environ['XDG_CONFIG_HOME'] = root
    os.environ['XDG_DATA_HOME'] = root
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    app = Nahj()
    result = {'passed': False, 'error': None}
    def begin(*_):
        app.address.set_text(f'http://127.0.0.1:{server.server_port}')
        app.language.set_selected(1)
        assert config.load()['language'] == 'en'
        # Changing UI language must not persist an unverified address.
        assert config.load()['server'] == ''
        app.connect_server()
        GLib.timeout_add(100, inspect)
    def inspect():
        try:
            if not app.web or app.web.get_title() != 'Nahj smoke':
                return True
            assert config.load()['server'].endswith(str(server.server_port))
            web, uri = app.web, app.web.get_uri()
            app.show_settings()
            old_generation = app.probe_generation
            app.address.set_text('https://unverified.invalid')
            app.language.set_selected(0)
            assert app.active_server.endswith(str(server.server_port))
            assert config.load()['server'] == app.active_server
            app.connected(old_generation, 'https://unverified.invalid', None)
            assert app.active_server.endswith(str(server.server_port)), 'stale callback changed server'
            app.show_web()
            assert app.web is web and app.web.get_uri() == uri, 'settings reloaded the current page'
            assert app.lookup_action('back') and app.lookup_action('reload')
            result['passed'] = True
        except Exception as error:
            result['error'] = repr(error)
        app.quit()
        return False
    app.connect('activate', begin)
    GLib.timeout_add_seconds(25, lambda: (app.quit(), False)[1])
    app.run([])
    server.shutdown(); server.server_close()
    assert result['passed'], result['error'] or 'Native WebKit page did not finish loading'
    print('PASS: window, language, connection, session, navigation, stale callbacks and draft preservation')
