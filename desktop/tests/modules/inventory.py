"""Inventory every ERPNext Python test file; do not infer exhaustive business coverage."""
import ast
import hashlib
import json
from pathlib import Path
import sys


def inventory(root, shards=8):
    root = Path(root)
    files = []
    for path in sorted((root / 'erpnext').rglob('test_*.py')):
        tree = ast.parse(path.read_text())
        count = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test_')
                    for n in ast.walk(tree))
        files.append(dict(path=str(path.relative_to(root)), methods=count,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    # Preserve upstream discovery order, assigning each whole file exactly once.
    target = sum(max(1, f['methods']) for f in files) / shards
    group, weight = 1, 0
    for f in files:
        if weight >= target and group < shards:
            group += 1
            weight = 0
        f['shard'] = group
        weight += max(1, f['methods'])
    return dict(shards=shards, files=files, modules=(root / 'erpnext/modules.txt').read_text().splitlines(),
                static_test_methods=sum(f['methods'] for f in files))


if __name__ == '__main__':
    json.dump(inventory(sys.argv[1]), sys.stdout, ensure_ascii=False, indent=2)
    print()
