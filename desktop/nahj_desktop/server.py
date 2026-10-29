"""Rootless Podman lifecycle. Persistent data is never removed by stop/retry.

The image archive must be the verified release asset. Credentials travel over
stdin or private files, never shell interpolation or command-line arguments.
"""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import uuid

from .connection import probe, ConnectionFailure

IMAGE_SHA256 = 'dc3c5731b34b63865c4e5320f1045f16c46b19dcc7bfaf1522ddc8d71a7553af'
# Config digest from the manifest in the above checksum-pinned release archive.
IMAGE_ID = 'sha256:46a6fb4e82c0f5f82f7b1d647ca2a4107f369e44d934093d92dbb1f140ee7c39'
BENCH = '/home/frappe/frappe-bench'


class ServerError(Exception):
    pass


def data_path():
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'nahj/server'


def private_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def validate(options):
    mode = options.get('mode')
    if mode not in ('local', 'external'):
        raise ServerError('Select local MariaDB or external MariaDB.')
    site = options.get('site', '').strip()
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,100}', site) or '..' in site:
        raise ServerError('Enter a valid site hostname.')
    try:
        port = int(options.get('port', 8088))
    except (ValueError, TypeError):
        raise ServerError('Invalid local HTTP port.') from None
    if not 1024 <= port <= 65535:
        raise ServerError('Local HTTP port must be between 1024 and 65535.')
    result = {'mode': mode, 'site': site, 'port': port,
              'language': 'en' if options.get('language') == 'en' else 'ar'}
    if mode == 'external':
        for key in ('db_host', 'db_name', 'db_user'):
            value = options.get(key, '').strip()
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', value):
                raise ServerError('Enter a valid database host, name and user.')
            result[key] = value
        try:
            result['db_port'] = int(options.get('db_port', 3306))
        except (ValueError, TypeError):
            raise ServerError('Invalid MariaDB port.') from None
        if not 1 <= result['db_port'] <= 65535:
            raise ServerError('Invalid MariaDB port.')
        ca = Path(options.get('ca', '')).expanduser()
        if not ca.is_file():
            raise ServerError('Select the CA certificate for the MariaDB server.')
        import ssl
        try:
            ssl.create_default_context(cafile=str(ca))
        except (OSError, ssl.SSLError):
            raise ServerError('Cannot load the MariaDB CA certificate.') from None
        result['ca'] = str(ca.resolve())
    return result


def compose_spec(profile, root):
    """JSON is valid Compose input; explicit labels avoid container-name guesses."""
    project = profile['project']
    common = {
        'image': profile['image'], 'working_dir': BENCH, 'restart': 'unless-stopped',
        'volumes': ['sites:' + BENCH + '/sites', 'logs:' + BENCH + '/logs'],
    }
    if profile['mode'] == 'external':
        common['volumes'].append(str(root / 'database-ca.pem') + ':/run/nahj/database-ca.pem:ro')
        common['volumes'].append(str(root / 'database-client.cnf') + ':/home/frappe/.my.cnf:ro')

    def service(name, command):
        return {**common, 'labels': {'io.nahj.project': project, 'io.nahj.service': name},
                'entrypoint': ['/home/frappe/entrypoint.sh'], 'command': command}

    services = {
        'backend': service('backend', ['env/bin/gunicorn', '--chdir=sites', '--bind', '0.0.0.0:8000',
                                     '--workers', '2', '--threads', '4', '--worker-class=gthread',
                                     '--timeout', '300', '--preload', 'frappe.app:application']),
        'websocket': service('websocket', ['node', 'apps/frappe/socketio.js']),
        'scheduler': service('scheduler', ['bench', 'schedule']),
        'worker': service('worker', ['bench', 'worker', '--queue', 'short,default,long']),
        'redis-cache': {'image': 'docker.io/library/redis:7-alpine', 'restart': 'unless-stopped'},
        'redis-queue': {'image': 'docker.io/library/redis:7-alpine', 'restart': 'unless-stopped',
                        'command': ['redis-server', '--appendonly', 'yes'], 'volumes': ['queue:/data']},
    }
    services['frontend'] = service('frontend', ['nginx-entrypoint.sh'])
    services['initializer'] = service('initializer', ['true'])
    services['initializer']['profiles'] = ['setup']
    services['frontend']['environment'] = {
        'BACKEND': 'backend:8000', 'SOCKETIO': 'websocket:9000',
        'FRAPPE_SITE_NAME_HEADER': profile['site'], 'PROXY_READ_TIMEOUT': '300',
        'CLIENT_MAX_BODY_SIZE': '100m',
    }
    services['frontend']['ports'] = [f"127.0.0.1:{profile['port']}:8080"]
    volumes = {key: {} for key in ('sites', 'logs', 'queue')}
    if profile['mode'] == 'local':
        services['db'] = {
            'image': 'docker.io/library/mariadb:11.8', 'restart': 'unless-stopped',
            'command': ['--character-set-server=utf8mb4', '--collation-server=utf8mb4_unicode_ci'],
            'environment': {'MARIADB_ROOT_PASSWORD_FILE': '/run/nahj/db-password'},
            'volumes': ['database:/var/lib/mysql', str(root / 'db-password') + ':/run/nahj/db-password:ro'],
        }
        volumes['database'] = {}
    return {'services': services, 'volumes': volumes}


class Server:
    def __init__(self, root=None, progress=None):
        self.root = Path(root) if root else data_path()
        self.progress = progress or (lambda message: None)
        self.redactions = []

    def run(self, args, *, payload=None, timeout=1800):
        try:
            result = subprocess.run(args, input=payload, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            raise ServerError('Podman/Podman Compose is missing. Install podman and podman-compose on Arch.') from None
        except subprocess.TimeoutExpired:
            raise ServerError('Operation timed out. Services and data were retained; inspect status before retrying.') from None
        if result.returncode:
            detail = (result.stderr or result.stdout)[-4000:]
            for secret in self.redactions:
                if secret:
                    detail = detail.replace(secret, '[redacted]')
            raise ServerError(f'Command failed ({result.returncode}): {detail}')
        return result.stdout

    @contextlib.contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with open(self.root / 'operation.lock', 'a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ServerError('Another service operation is still running.') from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def profile(self):
        try:
            return json.loads((self.root / 'profile.json').read_text())
        except (OSError, ValueError):
            raise ServerError('No managed site is configured. Set up a site first.') from None

    def compose(self, *args, payload=None):
        p = self.profile()
        return self.run(['podman', 'compose', '--project-name', p['project'],
                         '-f', str(self.root / 'compose.json'), *args], payload=payload)

    def backend(self):
        p = self.profile()
        ids = self.run(['podman', 'ps', '--filter', 'label=io.nahj.project=' + p['project'],
                        '--filter', 'label=io.nahj.service=backend', '--format', '{{.ID}}']).split()
        if len(ids) != 1:
            raise ServerError('Expected one running backend container. Start services and inspect status.')
        return ids[0]

    def import_image(self, archive):
        archive = Path(archive).expanduser()
        self.progress('Checking server image SHA256…')
        with archive.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != IMAGE_SHA256:
            raise ServerError('Server image checksum does not match release 0.3.0. Nothing was imported.')
        # The verified archive and image config have fixed digests. Avoid inflating
        # every layer merely to locate manifest.json, or importing an existing image.
        # Inspect by immutable ID so a changed local tag cannot select another image.
        try:
            inspected = self.run(['podman', 'image', 'inspect', IMAGE_ID])
        except ServerError:
            self.progress('Importing verified server image…')
            self.run(['podman', 'load', '--input', str(archive)])
            inspected = self.run(['podman', 'image', 'inspect', IMAGE_ID])
        info = json.loads(inspected)[0]
        if info['Id'].removeprefix('sha256:') != IMAGE_ID.removeprefix('sha256:'):
            raise ServerError('Imported image identity does not match release 0.3.0.')
        if info.get('Architecture') != 'amd64':
            raise ServerError('This server release requires an amd64 machine.')
        return info['Id']

    def setup(self, options, archive, admin_password, db_password=''):
        p = validate(options)
        if len(admin_password) < 12:
            raise ServerError('Choose an Administrator password of at least 12 characters.')
        if p['mode'] == 'external' and not db_password:
            raise ServerError('Enter the password for the existing empty MariaDB database.')
        self.redactions = [admin_password, db_password]
        with self.locked():
            if (self.root / 'profile.json').exists():
                raise ServerError('A site is already configured or partially initialized. Data was retained; do not overwrite it.')
            if self.run(['podman', 'info', '--format', '{{.Host.Security.Rootless}}']).strip() != 'true':
                raise ServerError('Run Nahj with rootless Podman as your normal desktop user.')
            if not archive:
                from .server_download import download
                archive = download(self.progress)
            p['image'] = self.import_image(archive)
            p['project'] = 'nahj-' + uuid.uuid4().hex[:12]
            if p['mode'] == 'external':
                private_write(self.root / 'database-ca.pem', Path(p.pop('ca')).read_text())
                # A CA certificate is public; the unprivileged container user needs to read it.
                (self.root / 'database-ca.pem').chmod(0o644)
                # Frappe's import/dump CLI does not pass db_ssl_ca itself.
                # Enforce certificate and hostname checks for those clients too.
                private_write(self.root / 'database-client.cnf',
                              '[client]\nssl-ca=/run/nahj/database-ca.pem\nssl-verify-server-cert=1\n')
                (self.root / 'database-client.cnf').chmod(0o644)
                self.progress('Checking the external MariaDB connection over TLS…')
                # The release image includes this read-only preflight. Reject bad
                # credentials/certificates/nonempty databases before saving a profile.
                self.run(['podman', 'run', '--rm', '-i', '--entrypoint', BENCH + '/env/bin/python',
                          '-v', str(self.root / 'database-ca.pem') + ':/run/nahj/ca.pem:ro',
                          p['image'], '/home/frappe/nahj-check-database.py'],
                         payload=json.dumps({'host': p['db_host'], 'port': p['db_port'],
                                             'user': p['db_user'], 'password': db_password,
                                             'database': p['db_name'], 'ca': True}))
            else:
                db_password = secrets.token_urlsafe(32)
                self.redactions.append(db_password)
                private_write(self.root / 'db-password', db_password)
            p['initialized'] = False
            private_write(self.root / 'profile.json', json.dumps(p))
            private_write(self.root / 'compose.json', json.dumps(compose_spec(p, self.root), indent=2))
            self.progress('Starting database and Redis…')
            self.compose('up', '-d', 'redis-cache', 'redis-queue', *(['db'] if p['mode'] == 'local' else []))
            self.progress('Creating the site and installing ERPNext. This may take several minutes…')
            payload = {**p, 'admin_password': admin_password, 'password': db_password}
            script = Path(__file__).with_name('provision.py').read_text()
            # Source is fixed application code. Secrets are JSON on stdin only.
            self.compose('run', '--rm', '-T', 'initializer', 'env/bin/python', '-c', script,
                         payload=json.dumps(payload))
            p['initialized'] = True
            private_write(self.root / 'profile.json', json.dumps(p))
            return self._start()

    def _start(self):
        p = self.profile()
        if not p.get('initialized'):
            raise ServerError('Site initialization did not complete. Inspect the setup error; existing data has been preserved.')
        self.progress('Starting services…')
        self.compose('up', '-d')
        self.progress('Waiting for ERPNext to respond…')
        origin = f"http://127.0.0.1:{p['port']}"
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            try:
                probe(origin)
                self.progress('ERPNext is ready: ' + origin)
                return origin
            except ConnectionFailure:
                time.sleep(2)
        raise ServerError('ERPNext did not become ready within 300 seconds. Inspect service status; data was retained.')

    def start(self):
        with self.locked():
            return self._start()

    def resume(self, admin_password='', db_password=''):
        """Resume app installation without dropping a database or changing passwords."""
        with self.locked():
            p = self.profile()
            if p.get('initialized'):
                return self._start()
            active = self.run(['podman', 'ps', '--filter', 'label=io.nahj.project=' + p['project'],
                               '--filter', 'label=io.nahj.service=initializer', '--format', '{{.ID}}']).strip()
            if active:
                raise ServerError('The original site initialization is still running. Wait for it to finish before resuming.')
            if p['mode'] == 'local':
                db_password = (self.root / 'db-password').read_text()
            self.redactions = [admin_password, db_password]
            self.progress('Resuming the saved site installation without replacing its data…')
            self.compose('up', '-d', 'redis-cache', 'redis-queue', *(['db'] if p['mode'] == 'local' else []))
            script = Path(__file__).with_name('provision.py').read_text()
            self.compose('run', '--rm', '-T', 'initializer', 'env/bin/python', '-c', script,
                         payload=json.dumps({**p, 'admin_password': admin_password, 'password': db_password}))
            p['initialized'] = True
            private_write(self.root / 'profile.json', json.dumps(p))
            return self._start()

    def stop(self):
        with self.locked():
            self.progress('Stopping services; database and files will be retained…')
            self.compose('stop', '--timeout', '60')
            self.progress('Services stopped. Database and files retained.')

    def status(self):
        return self.compose('ps', '--all')

    def backup(self, destination):
        """Export only this invocation's files from the backend selected by labels."""
        if not str(destination).strip():
            raise ServerError('Select an existing backup destination folder.')
        with self.locked():
            p = self.profile()
            container = self.backend()
            target = Path(destination).expanduser().resolve()
            if not target.is_dir():
                raise ServerError('Select an existing backup destination folder.')
            token = 'nahj-backup-' + uuid.uuid4().hex
            remote = '/tmp/' + token
            stage = Path(tempfile.mkdtemp(prefix='.' + token, dir=target))
            try:
                self.progress('Backing up database, public/private files and site configuration…')
                self.run(['podman', 'exec', container, 'bench', '--site', p['site'], 'backup',
                          '--with-files', '--compress', '--backup-path', remote])
                self.run(['podman', 'cp', container + ':' + remote + '/.', str(stage)])
                self.run(['podman', 'cp', container + ':' + BENCH + '/sites/common_site_config.json',
                          str(stage / 'common_site_config.json')])
                if p['mode'] == 'external':
                    shutil.copyfile(self.root / 'database-ca.pem', stage / 'database-ca.pem')
                    shutil.copyfile(self.root / 'database-client.cnf', stage / 'database-client.cnf')
                files = [f for f in stage.iterdir() if f.is_file() and not f.is_symlink()]
                names = [f.name for f in files]
                for suffixes in (('database.sql.gz',), ('-files.tar', '-files.tgz'),
                                 ('-private-files.tar', '-private-files.tgz'), ('site_config_backup.json',)):
                    candidates = [n for n in names if n.endswith(suffixes)]
                    if suffixes[0] == '-files.tar':
                        candidates = [n for n in candidates if '-private-files.' not in n]
                    if not candidates:
                        raise ServerError('Incomplete backup: missing ' + suffixes[0])
                checksums = {}
                for file in files:
                    if file.stat().st_size == 0:
                        raise ServerError('Backup contains an empty file: ' + file.name)
                    file.chmod(0o600)
                    with file.open('rb') as stream:
                        checksums[file.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
                private_write(stage / 'manifest.json', json.dumps({'site': p['site'], 'sha256': checksums}, indent=2))
                final = target / token
                stage.rename(final)
                self.progress('Backup exported: ' + str(final))
                return final
            finally:
                if stage.exists():
                    shutil.rmtree(stage)
                # Only delete the unique temporary container directory from this invocation.
                try:
                    self.run(['podman', 'exec', container, 'rm', '-rf', '--', remote], timeout=30)
                except ServerError:
                    pass
