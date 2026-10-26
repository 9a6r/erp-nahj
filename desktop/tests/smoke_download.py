"""Verify WebKit downloads and native save/cancel handling with a local server."""
import os
from pathlib import Path
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import subprocess

from nahj_desktop.app import Nahj, GLib
from nahj_desktop import config

PAYLOAD = b'date,amount\n2026-10-26,125.00\n'


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        if self.path == '/download':
            self.send_header('Content-Type', 'text/csv')
            self.send_header('Content-Disposition', 'attachment; filename="statement.csv"')
            payload = PAYLOAD
        elif self.path.startswith('/api/'):
            self.send_header('Content-Type', 'application/json')
            payload = b'{"message":"pong"}'
        else:
            self.send_header('Content-Type', 'text/html')
            payload = b'<html><title>Download test</title><body>Ready</body></html>'
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_):
        pass


with tempfile.TemporaryDirectory() as root:
    os.environ['XDG_CONFIG_HOME'] = root
    os.environ['XDG_DATA_HOME'] = root
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    destination = Path(root) / 'statement.csv'
    config.save({'server': '', 'language': 'en'})
    app = Nahj()
    state = {'stage': 'connect', 'dialog': None, 'done': False, 'error': None, 'finished': False, 'cancelled': False}
    def save_window():
        result = subprocess.run(['xdotool', 'search', '--onlyvisible', '--name', '^Save file$'], capture_output=True, text=True)
        return result.stdout.splitlines()[0] if result.returncode == 0 else None

    def key(window, *keys):
        subprocess.run(['xdotool', 'windowactivate', '--sync', window], check=True)
        subprocess.run(['xdotool', 'key', '--clearmodifiers', *keys], check=True)

    def started(session, download):
        download.connect('finished', lambda item: (print('Download destination:', item.get_destination(), flush=True), state.update(finished=True)))
        download.connect('failed', lambda item, error: (print('Download result:', error.message, flush=True), state.update(cancelled=True)))

    def begin(*_):
        app.address.set_text(origin)
        app.connect_server()
        GLib.timeout_add(200, tick)

    def tick():
        try:
            if state['stage'] == 'connect' and app.web and app.web.get_title() == 'Download test':
                app.web.get_network_session().connect('download-started', started)
                app.web.download_uri(origin + '/download')
                state['stage'] = 'save'
            elif state['stage'] == 'save':
                window = save_window()
                if window:
                    key(window, 'ctrl+l')
                    state['window'] = window
                    state['stage'] = 'type'
            elif state['stage'] == 'type':
                key(state['window'], 'ctrl+a')
                subprocess.run(['xdotool', 'type', '--clearmodifiers', '--delay', '20', str(destination)], check=True)
                key(state['window'], 'Return')
                state['stage'] = 'saved'
            elif state['stage'] == 'saved' and state['finished']:
                assert destination.read_bytes() == PAYLOAD, 'Downloaded bytes do not match'
                assert not app.error_banner.get_visible(), 'Successful download showed an error'
                app.web.download_uri(origin + '/download')
                state['stage'] = 'cancel'
            elif state['stage'] == 'cancel':
                window = save_window()
                if window:
                    key(window, 'Escape')
                    state['stage'] = 'cancelled'
            elif state['stage'] == 'cancelled' and state['cancelled']:
                assert destination.read_bytes() == PAYLOAD, 'Cancellation modified the saved file'
                assert not app.error_banner.get_visible(), 'User cancellation showed an error'
                state['done'] = True
                app.quit()
                return False
        except Exception as error:
            state['error'] = repr(error)
            app.quit()
            return False
        return True

    app.connect('activate', begin)
    GLib.timeout_add_seconds(180, lambda: (app.quit(), False)[1])
    app.run([])
    server.shutdown()
    server.server_close()
    assert state['done'], state['error'] or f'Download test timed out at {state["stage"]}'
    print('PASS: WebKit download, native save destination, exact file content and cancellation')
