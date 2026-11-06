"""Verify that Nahj retains the pinned ERPNext tree outside reviewed overlays."""
import argparse
import json
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[2]
CHANGED = {
    'erpnext/controllers/accounts_controller.py': 'Print-language amount-in-words only',
    'erpnext/controllers/print_settings.py': 'Translated units in printed item tables',
    'erpnext/locale/ar.po': 'Arabic catalogue completion and corrections',
    'erpnext/www/banking.py': 'Authenticated language preference and language-aware boot',
}
ADDED = {
    'erpnext/templates/print_formats/includes/item_table_uom.html',
    'erpnext/tests/test_banking_language.py',
}
ROOT_FILES = ('pyproject.toml', 'package.json', 'yarn.lock', 'license.txt')


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])


def tree(ref):
    result = {}
    for row in git('ls-tree', '-rz', ref, '--', 'erpnext', *ROOT_FILES).split(b'\0'):
        if row:
            properties, path = row.split(b'\t', 1)
            result[path.decode()] = properties.decode()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', default='HEAD', help='Committed tree to audit')
    args = parser.parse_args()
    release = json.loads((REPO / 'desktop/server-image/upstream.json').read_text())
    base = release['erpnext_commit']
    original, current = tree(base), tree(args.ref)
    deleted = sorted(original.keys() - current.keys())
    unexpected = sorted(path for path in current.keys() - original.keys() if path not in ADDED)
    changed = sorted(path for path in original.keys() & current.keys()
                     if original[path] != current[path])
    unreviewed = sorted(set(changed) - CHANGED.keys())
    if deleted or unexpected or unreviewed:
        raise SystemExit(json.dumps({'deleted': deleted, 'unexpected_added': unexpected,
                                     'unreviewed_changes': unreviewed}, indent=2))
    app_files = [path for path in original if path.startswith('erpnext/')]
    doctypes = [path for path in app_files if '/doctype/' in path and path.endswith('.json')
                and Path(path).stem == Path(path).parent.name]
    reports = [path for path in app_files if '/report/' in path and path.endswith('.json')
               and Path(path).stem == Path(path).parent.name]
    modules = git('show', base + ':erpnext/modules.txt').decode().splitlines()
    print(json.dumps({'upstream_version': release['erpnext_version'], 'upstream_commit': base,
        'audited_ref': git('rev-parse', args.ref).decode().strip(), 'original_app_files': len(app_files),
        'unchanged_app_files': len(app_files) - len(changed), 'deleted': deleted,
        'unchanged_doctype_definitions': len(doctypes), 'unchanged_report_definitions': len(reports),
        'modules': modules, 'reviewed_changes': {path: CHANGED[path] for path in changed},
        'added': sorted(current.keys() - original.keys()), 'root_build_metadata_unchanged': True},
        ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
