"""Resumable release download with mandatory SHA256 verification."""
import hashlib
import os
from pathlib import Path
from urllib.request import Request, urlopen

from .server import IMAGE_SHA256, ServerError, data_path

URL = 'https://github.com/9a6r/erp-nahj/releases/download/desktop-v0.3.0/nahj-server-0.3.0-amd64.tar.gz'
SIZE = 1370682143


def download(progress, cache=None):
    cache = Path(cache) if cache else data_path().parent / 'downloads'
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    final = cache / 'nahj-server-0.3.0-amd64.tar.gz'
    partial = final.with_suffix(final.suffix + '.part')
    if final.exists():
        with final.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() == IMAGE_SHA256:
                return final
        raise ServerError('The cached server image failed verification. Select a verified archive or remove the damaged download.')
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > SIZE:
        raise ServerError('The partial download exceeds the expected image size.')
    if offset < SIZE:
        request = Request(URL, headers={'Range': f'bytes={offset}-'} if offset else {})
        with urlopen(request, timeout=60) as response:
            if response.status == 206:
                if not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                    raise ServerError('The download server returned an unexpected byte range.')
            elif response.status == 200:
                offset = 0  # Server does not support resume; replace only the partial file.
            else:
                raise ServerError('Unexpected download response.')
            with partial.open('ab' if offset else 'wb') as output:
                os.chmod(partial, 0o600)
                previous = -1
                while chunk := response.read(1024 * 1024):
                    if offset + len(chunk) > SIZE:
                        raise ServerError('The download exceeds the expected image size.')
                    output.write(chunk)
                    offset += len(chunk)
                    percent = offset * 100 // SIZE
                    if percent != previous:
                        progress(f'Downloading server: {percent}%')
                        previous = percent
    if offset != SIZE:
        raise ServerError('Download interrupted; retry to resume it.')
    progress('Checking server image SHA256…')
    with partial.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != IMAGE_SHA256:
            raise ServerError('Downloaded image failed SHA256 verification. No services were started.')
    partial.replace(final)
    return final
