import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from nahj_desktop import config

class ConfigTests(unittest.TestCase):
    def test_urls(self):
        for value in ('https://erp.example.com/', 'http://127.0.0.1:8000', 'http://nahj.localhost:8000'):
            self.assertEqual(config.server_url(value), value.rstrip('/'))
        for value in ('file:///etc/passwd', 'javascript:alert(1)', 'https://user:pass@host', 'http://example.com', 'https://host/app', 'https://host?token=secret', 'https://host:bad', 'https://host/#token'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                config.server_url(value)

    def test_roundtrip_and_corruption(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'XDG_CONFIG_HOME': root}):
            self.assertEqual(config.load()['language'], 'ar')
            config.save({'server':'https://erp.example.com', 'language':'en', 'token':'never persist'})
            self.assertEqual(config.load(), {'server':'https://erp.example.com', 'language':'en'})
            self.assertNotIn('token', json.loads(config.config_path().read_text()))
            self.assertEqual(config.config_path().stat().st_mode & 0o777, 0o600)
            config.config_path().write_text('invalid')
            self.assertEqual(config.load()['server'], '')


class PreferenceTests(unittest.TestCase):
    def test_canonical_origins(self):
        self.assertEqual(config.server_url('HTTPS://ERP.Example.com:443/'), 'https://erp.example.com')
        self.assertEqual(config.server_url('http://[::1]:8000'), 'http://[::1]:8000')
        self.assertEqual(config.server_url('http://LOCALHOST.:80'), 'http://localhost')
        for address in ['https://host:0', 'https://host name', 'https://host\\evil', 'http://localhost.evil.example', 'https://@host']:
            with self.subTest(address=address), self.assertRaises(ValueError):
                config.server_url(address)

    def test_language_can_be_saved_before_connection(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'XDG_CONFIG_HOME': root}):
            config.save({'server': '', 'language': 'en'})
            self.assertEqual(config.load(), {'server': '', 'language': 'en'})
            config.config_path().write_text('[]')
            self.assertEqual(config.load()['server'], '')

if __name__ == '__main__': unittest.main()
