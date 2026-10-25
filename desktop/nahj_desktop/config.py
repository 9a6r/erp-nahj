"""Preferences and canonical server origins."""
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit


def server_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value.strip()):
        raise ValueError('Invalid server address')
    url = urlsplit(value.strip())
    if url.scheme not in ('https', 'http') or not url.hostname or url.username is not None or url.password is not None:
        raise ValueError('Enter a server URL without credentials')
    if url.path not in ('', '/') or url.query or url.fragment or '\\' in value:
        raise ValueError('Use the server origin, without a path or query')
    host = url.hostname.rstrip('.').encode('idna').decode('ascii').lower()
    if not host or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-.:' for c in host):
        raise ValueError('Invalid hostname')
    if url.scheme == 'http' and host not in ('localhost', '127.0.0.1', '::1') and not host.endswith('.localhost'):
        raise ValueError('Remote servers must use HTTPS')
    port = url.port
    if port == 0:
        raise ValueError('Invalid port')
    authority = f'[{host}]' if ':' in host else host
    if port and port != (443 if url.scheme == 'https' else 80):
        authority += f':{port}'
    return f'{url.scheme}://{authority}'


def config_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'nahj' / 'settings.json'


def normalize(value):
    return {'server': server_url(value['server']) if value.get('server') else '',
            'language': 'en' if value.get('language') == 'en' else 'ar'}


def load():
    try:
        return normalize(json.loads(config_path().read_text()))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {'server': '', 'language': 'ar'}


def save(value):
    data = normalize(value)
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # mkstemp creates a private file before writing; replace is atomic.
    fd, name = tempfile.mkstemp(prefix='.settings-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
