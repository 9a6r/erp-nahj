"""Real WebKit executes authenticated language changes; local fixture owns the API."""
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from nahj_desktop.app import Nahj, GLib
from nahj_desktop import config

state = {'language': 'ar', 'deny': False, 'changes': []}


class Handler(BaseHTTPRequestHandler):
    def reply(self, data, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(data.encode())

    def do_GET(self):
        if self.path.startswith('/api/method/ping'):
            self.reply('{"message":"pong"}')
        elif self.path.startswith('/api/method/frappe.auth.get_logged_user'):
            self.reply('{"message":"test@example.test"}')
        else:
            language = state['language']
            self.reply(f'<html lang="{language}"><title>Nahj {language}</title>'
                       '<script>window.frappe={csrf_token:"test-csrf"};</script>'
                       '<body><input value="unsaved draft"></body></html>', content_type='text/html')

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if (state['deny'] or self.path != '/api/method/frappe.client.set_value'
                or self.headers.get('X-Frappe-CSRF-Token') != 'test-csrf'
                or data.get('doctype') != 'User' or data.get('name') != 'test@example.test'
                or data.get('fieldname') != 'language' or data.get('value') not in ('ar', 'en')):
            self.reply('{}', status=403)
            return
        state['language'] = data['value']
        state['changes'].append(data['value'])
        self.reply(json.dumps({'message': {'language': data['value']}}))

    def log_message(self, *_):
        pass


with tempfile.TemporaryDirectory() as root:
    os.environ['XDG_CONFIG_HOME'] = root
    os.environ['XDG_DATA_HOME'] = root
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    app = Nahj()
    result = {'passed': False, 'stage': 0, 'error': None}

    def begin(*_):
        app.address.set_text(f'http://127.0.0.1:{server.server_port}')
        app.connect_server()
        GLib.timeout_add(100, inspect)

    def inspect():
        try:
            if not app.web or app.web.is_loading() or getattr(app, 'language_operation', False):
                return True
            stage = result['stage']
            if stage == 0 and app.web.get_title() == 'Nahj ar':
                app.change_workspace_language('en')
                result['stage'] = 1
            elif stage == 1 and app.web.get_title() == 'Nahj en':
                assert app.settings['language'] == config.load()['language'] == 'en'
                app.change_workspace_language('ar')
                result['stage'] = 2
            elif stage == 2 and app.web.get_title() == 'Nahj ar':
                assert app.settings['language'] == config.load()['language'] == 'ar'
                assert state['changes'] == ['en', 'ar']
                result['uri'] = app.web.get_uri()
                state['deny'] = True
                app.change_workspace_language('en')
                result['stage'] = 3
            elif stage == 3 and app.error_banner.get_visible():
                assert app.settings['language'] == config.load()['language'] == 'ar'
                assert app.web.get_uri() == result['uri']
                assert state['changes'] == ['en', 'ar']
                result['passed'] = True
                app.quit()
                return False
        except Exception as error:
            result['error'] = repr(error)
            app.quit()
            return False
        return True

    app.connect('activate', begin)
    GLib.timeout_add_seconds(90, lambda: (app.quit(), False)[1])
    app.run([])
    server.shutdown()
    server.server_close()
    assert result['passed'], result['error'] or f"Language test stalled at stage {result['stage']}"
    print('PASS: WebKit persists Arabic/English via session and CSRF; API rejection preserves settings and page')
