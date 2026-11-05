"""Real, unmodified Server controller on a disposable Arch/Zen rootless VM.

No Docker adapter, image-identity override, shared network namespace or combined
application container is allowed. Private state remains in the disposable VM.
"""
import argparse
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import subprocess
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, ProxyHandler, HTTPCookieProcessor, Request

from nahj_desktop.server import Server, private_write, BENCH

ROOT = Path.home() / 'nahj-full-validation'
TESTS = Path(__file__).resolve().parent
ARCHIVE = Path.home() / 'server.tar.gz'


def report(message):
    print(message, flush=True)


def controller(name):
    return Server(root=ROOT / name, progress=report)


def inside(server, code, data=None):
    return server.run(['podman', 'exec', '-i', server.backend(), 'env/bin/python', '-c', code],
                      payload=json.dumps(data) if data is not None else None)


def run_test(server, name, data=None):
    container = server.backend()
    server.run(['podman', 'cp', str(TESTS / name), container + ':/tmp/' + name])
    output = server.run(['podman', 'exec', '-i', '-e', 'NAHJ_ACCEPTANCE_SITE=' + server.profile()['site'],
                         '-e', 'NAHJ_SERVICE_RECEIVER_HOST=backend', '-w', BENCH + '/sites',
                         container, '../env/bin/python', '/tmp/' + name],
                        payload=json.dumps(data) if data is not None else None, timeout=900)
    report(output)


def topology(server, pending=False):
    project = server.profile()['project']
    ids = server.run(['podman', 'ps', '-q', '--filter', 'label=io.podman.compose.project=' + project]).split()
    assert ids, 'Compose project labels did not identify running containers'
    containers = json.loads(server.run(['podman', 'inspect', *ids]))
    names = set()
    for container in containers:
        labels = container['Config']['Labels']
        name = labels.get('com.docker.compose.service') or labels.get('io.podman.compose.service')
        assert name and name not in names, 'Expected a separate container for every service'
        names.add(name)
        mode = container['HostConfig']['NetworkMode']
        assert mode != 'host' and not mode.startswith('container:'), 'Shared network namespace is not accepted'
        assert container['State']['Running']
    expected = {'backend', 'frontend', 'websocket', 'db', 'redis-cache', 'redis-queue'}
    if not pending:
        expected |= {'worker', 'scheduler'}
    assert names == expected, (names, expected)
    report('PASS: separate rootless containers: ' + ', '.join(sorted(names)))


def http_checks(server, state):
    origin = 'http://127.0.0.1:' + str(server.profile()['port'])
    client = build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))
    guest = build_opener(ProxyHandler({}))

    def request(opener, path, data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-Frappe-CSRF-Token'] = token
        req = Request(origin + path, data=json.dumps(data).encode() if data else None, headers=headers)
        with opener.open(req, timeout=180) as response:
            return response.read()

    try:
        request(guest, '/api/method/login', {'usr': 'Administrator', 'pwd': 'wrong-validation-password'})
    except HTTPError as error:
        assert error.code in (401, 403)
        error.close()
    else:
        raise AssertionError('Incorrect password accepted')
    request(client, '/api/method/login', {'usr': 'Administrator', 'pwd': state['admin']})
    for attachment in state['records']['files']:
        if attachment['private']:
            try:
                request(guest, attachment['url'])
            except HTTPError as error:
                assert error.code in (401, 403, 404)
                error.close()
            else:
                raise AssertionError('Unauthenticated private file access')
        else:
            assert hashlib.sha256(request(guest, attachment['url'])).hexdigest() == attachment['sha256']
        assert hashlib.sha256(request(client, attachment['url'])).hexdigest() == attachment['sha256']
    page = request(client, '/desk').decode()
    csrf = re.search(r'frappe.csrf_token\s*=\s*"([^"]+)"', page).group(1)
    for language, direction in (('ar', 'rtl'), ('en', 'ltr'), ('ar', 'rtl')):
        result = json.loads(request(client, '/api/method/frappe.client.set_value',
            {'doctype': 'User', 'name': 'Administrator', 'fieldname': 'language', 'value': language}, csrf))
        assert result['message']['language'] == language
        page = request(client, '/desk').decode()
        root = re.search(r'<html[^>]*>', page).group(0)
        assert f'lang="{language}"' in root and f'dir={direction}' in root
    banking = request(client, '/banking').decode()
    asset = re.search(r'src="(/assets/erpnext/banking/[^\"]+\.js)"', banking)
    assert asset and request(client, asset.group(1))
    query = urlencode({'doctype': 'Sales Invoice', 'name': state['records']['sales_invoice'],
                       'format': 'Standard', 'no_letterhead': 1, '_lang': 'ar', 'language': 'ar'})
    pdf = request(client, '/api/method/frappe.utils.print_format.download_pdf?' + query)
    assert pdf.startswith(b'%PDF-') and len(pdf) > 1000
    report('PASS: real HTTP login/denial, file authorization, persistent language, banking assets and invoice PDF')


def verify(server, state, pending=False):
    topology(server, pending)
    run_test(server, 'integration_verify.py', {**state, 'pending': pending})
    run_test(server, 'integration_arabic.py', state)
    http_checks(server, state)


def prepare():
    if ROOT.exists():
        raise RuntimeError('Refusing to overwrite previous validation data')
    ROOT.mkdir(mode=0o700)
    user = pwd.getpwuid(os.getuid()).pw_name
    if not any(line.startswith(user + ':') for line in Path('/etc/subuid').read_text().splitlines()):
        subprocess.run(['sudo', 'usermod', '--add-subuids', '200000-265535',
                        '--add-subgids', '200000-265535', user], check=True)
    original = controller('original')
    state = {'admin': secrets.token_urlsafe(32), 'canary': secrets.token_urlsafe(32)}
    private_write(ROOT / 'state.json', json.dumps(state))
    original.setup({'mode': 'local', 'site': 'nahj-validation.localhost', 'port': 18088,
                    'language': 'ar'}, str(ARCHIVE), state['admin'])
    topology(original)
    inside(original, '''import json, os, sys
from pathlib import Path
import frappe
from frappe.utils.password import set_encrypted_password
p = json.load(sys.stdin)
os.chdir('/home/frappe/frappe-bench/sites')
path = Path(p['site'], 'site_config.json')
config = json.loads(path.read_text()); config['nahj_disposable_test_site'] = True
path.write_text(json.dumps(config)); path.chmod(0o600)
frappe.init(p['site'], sites_path='.'); frappe.connect()
set_encrypted_password('User', 'Administrator', p['canary'], 'nahj_validation_canary')
frappe.db.commit(); frappe.destroy()
''', {'site': original.profile()['site'], 'canary': state['canary']})
    run_test(original, 'integration_business.py')
    state['records'] = json.loads(inside(original, '''from pathlib import Path
print(Path('sites/nahj-validation.localhost/private/nahj-acceptance.json').read_text())'''))
    private_write(ROOT / 'state.json', json.dumps(state))
    verify(original, state)
    run_test(original, 'integration_services.py')
    backups = ROOT / 'backups'
    backups.mkdir(mode=0o700)
    backup = original.backup(backups)
    original.verify_backup(backup)
    original.stop()
    restored = controller('restored')
    restored.restore(backup, {'mode': 'local', 'site': 'nahj-validation-restored.localhost',
                              'port': 18090, 'language': 'ar'}, str(ARCHIVE))
    # Recovery deliberately preserves only portable config; re-authorize tests
    # on this newly created disposable site, never on a general restored site.
    inside(restored, '''import json, sys
from pathlib import Path
site = json.load(sys.stdin)['site']
assert site == 'nahj-validation-restored.localhost'
path = Path('sites', site, 'site_config.json')
config = json.loads(path.read_text()); config['nahj_disposable_test_site'] = True
path.write_text(json.dumps(config)); path.chmod(0o600)
''', {'site': restored.profile()['site']})
    verify(restored, state, pending=True)
    restored.complete_recovery()
    verify(restored, state)
    run_test(restored, 'integration_services.py')
    restored.stop()
    report('PASS: full ERP created, transacted, backed up and recovered using the actual rootless controller')


def after_reboot():
    state = json.loads((ROOT / 'state.json').read_text())
    restored = controller('restored')
    restored.start()
    verify(restored, state)
    restored.stop()
    original = controller('original')
    original.start()
    verify(original, state)
    original.stop()
    report('PASS: original and restored full ERP stacks retain business data and secrets after a complete Zen VM reboot')


def diagnostics():
    """Print service state and routing only, never configs, environment or data."""
    for name in ('original', 'restored'):
        server = controller(name)
        if not (server.root / 'profile.json').is_file():
            continue
        try:
            project = server.profile()['project']
            ids = server.run(['podman', 'ps', '-aq', '--filter', 'label=io.podman.compose.project=' + project]).split()
            if not ids:
                continue
            containers = json.loads(server.run(['podman', 'inspect', *ids]))
            for container in containers:
                labels = container['Config']['Labels']
                service = labels.get('com.docker.compose.service') or labels.get('io.podman.compose.service')
                report(json.dumps({'project': name, 'service': service,
                    'status': container['State']['Status'], 'exit_code': container['State']['ExitCode'],
                    'oom_killed': container['State'].get('OOMKilled'),
                    'addresses': [v.get('IPAddress') for v in container['NetworkSettings']['Networks'].values()]}))
                if service == 'backend' and container['State']['Running']:
                    output = server.run(['podman', 'exec', container['Id'], 'env/bin/python', '-c',
                        "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/api/method/ping',timeout=10); print(r.status, r.read(100))"], timeout=20)
                    report('Direct backend ping: ' + output)
        except Exception as error:
            report('Diagnostic unavailable: ' + type(error).__name__)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'after-reboot'))
    args = parser.parse_args()
    if os.getuid() == 0 or 'zen' not in os.uname().release:
        raise SystemExit('Run as an ordinary user in the disposable Arch/Zen VM')
    try:
        (prepare if args.phase == 'prepare' else after_reboot)()
    except Exception:
        diagnostics()
        raise
