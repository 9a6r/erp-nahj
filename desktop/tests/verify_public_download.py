"""Exercise the real public download and resume path after release publication."""
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

from nahj_desktop import server_download

cache = Path(sys.argv[1])
cache.mkdir(parents=True, exist_ok=False)
partial = (cache / server_download.FILENAME).with_suffix('.gz.part')
length = 2 * 1024 * 1024
with urlopen(Request(server_download.URL, headers={'Range': f'bytes=0-{length-1}'}), timeout=60) as response:
    assert response.status == 206
    assert response.headers.get('Content-Range') == f'bytes 0-{length-1}/{server_download.SIZE}'
    data = response.read(length + 1)
    assert len(data) == length
    partial.write_bytes(data)
path = server_download.download(print, cache=cache)
assert path.stat().st_size == server_download.SIZE
assert not partial.exists()
with path.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
assert digest == server_download.IMAGE_SHA256
assert server_download.download(print, cache=cache) == path
(cache / 'public-download-proof.json').write_text(json.dumps({
    'url': server_download.URL, 'size': path.stat().st_size, 'sha256': digest,
    'range_status': 206, 'seeded_partial_bytes': length,
    'resumed_with_production_downloader': True, 'verified_cache_reused': True,
}, indent=2) + '\n')
print('PASS: public HTTP range, resumed production download, SHA256 and verified cache reuse')
