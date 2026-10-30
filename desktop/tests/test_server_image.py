import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch


class ServerImageTests(unittest.TestCase):
    def test_flatten_replaces_paths_and_binds_config_to_the_actual_layer(self):
        spec = importlib.util.spec_from_file_location('nahj_image_build', Path(__file__).parents[1] / 'server-image/build.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / 'repo'
            for name in ('erpnext/www/banking.py', 'erpnext/www/banking.html',
                         'erpnext/tests/test_banking_language.py', 'erpnext/public/banking/index.html'):
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'new verified source')
            rootfs = root / 'rootfs.tar'
            replaced = 'home/frappe/frappe-bench/apps/erpnext/erpnext/www/banking.py'
            with tarfile.open(rootfs, 'w') as archive:
                for name, data in ((replaced, b'upstream'), (replaced, b'old duplicate'), ('etc/test', b'preserve')):
                    builder.add_bytes(archive, name, data)
            destination = root / 'server.tar.gz'
            with patch.object(builder, 'REPO', repo):
                metadata = builder.package(rootfs, {'architecture': 'amd64', 'os': 'linux', 'config': {}}, destination)
            with tarfile.open(rootfs) as layer:
                self.assertEqual(len(layer.getnames()), len(set(layer.getnames())))
                self.assertEqual(layer.extractfile(replaced).read(), b'new verified source')
                self.assertEqual(layer.extractfile('etc/test').read(), b'preserve')
            with tarfile.open(destination) as archive:
                manifest = json.load(archive.extractfile('manifest.json'))[0]
                config_bytes = archive.extractfile(manifest['Config']).read()
                config = json.loads(config_bytes)
                self.assertEqual(metadata['image_id'], 'sha256:' + hashlib.sha256(config_bytes).hexdigest())
                self.assertEqual(config['rootfs']['diff_ids'], ['sha256:' + builder.sha256(rootfs)])


if __name__ == '__main__':
    unittest.main()
