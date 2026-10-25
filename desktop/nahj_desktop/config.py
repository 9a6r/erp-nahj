"""Non-secret preferences and strict server URL validation."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


def server_url(value):
    url = urlsplit(value.strip())
    if url.scheme not in ('https', 'http') or not url.hostname or url.username or url.password:
        raise ValueError('Enter a server URL without credentials.')
    if url.path not in ('', '/') or url.query or url.fragment:
        raise ValueError('Use the server origin, without a path or query.')
    if url.scheme == 'http' and url.hostname not in ('localhost', '127.0.0.1', '::1') and not url.hostname.endswith('.localhost'):
        raise ValueError('Remote servers must use HTTPS.')
    _ = url.port  # validates malformed ports
    return f'{url.scheme}://{url.netloc}'.rstrip('/')


def config_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'nahj' / 'settings.json'


def load():
    try:
        value = json.loads(config_path().read_text())
        return {'server': server_url(value['server']), 'language': 'en' if value.get('language') == 'en' else 'ar'}
    except (OSError, ValueError, KeyError, TypeError):
        return {'server': '', 'language': 'ar'}


def save(value):
    data = {'server': server_url(value['server']), 'language': 'en' if value.get('language') == 'en' else 'ar'}
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data))
    temp.chmod(0o600)
    temp.replace(path)
