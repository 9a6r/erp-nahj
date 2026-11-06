import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('rootless_setup', Path(__file__).parents[1] / 'setup_rootless.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class RootlessSetupTests(unittest.TestCase):
    def test_find_gap_without_overlapping_users_or_groups(self):
        self.assertEqual(setup.available_range([]), '100000-165535')
        self.assertEqual(setup.available_range([(100000, 65536), (150000, 65536), (400000, 65536)]),
                         '215536-281071')
        self.assertEqual(setup.available_range([(100005, 1)]), '100006-165541')
        with self.assertRaises(ValueError):
            setup.available_range([(100000, 600000001)])

    def test_preserve_named_and_numeric_mapping_owners(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'subuid'
            path.write_text('# comment\nexisting:100000:65536\n1000:200000:65536\n')
            self.assertEqual(setup.read_ranges(path), [('existing', 100000, 65536), ('1000', 200000, 65536)])
            path.write_text('broken:10:0\n')
            with self.assertRaises(ValueError):
                setup.read_ranges(path)
