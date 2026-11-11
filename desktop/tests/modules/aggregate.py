"""Summarize actual outcomes; missing files, skipped tests and partial runs stay visible."""
import collections
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
plans = list(root.glob('*/inventory.json'))
if not plans:
    raise SystemExit('No inventory artifacts were produced')
plan = json.loads(plans[0].read_text())
rows = {m: collections.Counter() for m in plan['modules']}
labels = {m.lower().replace(' ', '_'): m for m in plan['modules']}
labels['templates'] = 'Portal'

def owner(path):
    key = path.split('/')[1]
    return labels.get(key, 'Shared: ' + key)

for item in plan['files']:
    row = rows.setdefault(owner(item['path']), collections.Counter())
    row['files'] += 1
    row['declared_methods'] += item['methods']
seen_shards = set()
finished = set()
module_errors = []
failures = []
for directory in sorted(root.iterdir()):
    if not directory.is_dir():
        continue
    summary = directory / 'summary.json'
    if summary.exists():
        data = json.loads(summary.read_text())
        if data.get('smoke'):
            continue
        if data['shard'] in seen_shards:
            raise SystemExit('Duplicate shard results')
        seen_shards.add(data['shard'])
    events = directory / 'events.jsonl'
    if not events.exists():
        continue
    current = None
    for line in events.read_text().splitlines():
        event = json.loads(line)
        if 'module' in event:
            current = event['module']
        if not current:
            raise SystemExit('Test event has no module provenance')
        row = rows.setdefault(owner(current), collections.Counter())
        status = event['status']
        if status == 'finished':
            if current in finished:
                raise SystemExit('Duplicate module execution: ' + current)
            finished.add(current)
            row['executed'] += event['executed']
            row['completed_files'] += 1
        elif status == 'module_error':
            row[status] += 1
            module_errors.append(event)
        elif status != 'started':
            row[status] += 1
            if status in ('failed', 'error', 'unexpected_success', 'subtest_failure'):
                failures.append(dict(module=current, **event))
missing = sorted(set(range(1, plan['shards']+1)) - seen_shards)
unexecuted = sorted(x['path'] for x in plan['files'] if x['path'] not in finished)
result = dict(modules=rows, missing_shards=missing, unfinished_files=unexecuted,
              module_errors=module_errors, failures=failures,
              complete=not missing and not unexecuted and not module_errors,
              static_test_methods=plan['static_test_methods'])
(root/'outcomes.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
lines = ['# ERPNext upstream test outcomes', '',
         'This is execution of the existing upstream test suite, not proof of every possible business process.',
         'Portal includes website/template tests. Shared components are listed separately.', '',
         '| Module | Files | Declared methods | Executed tests | Passed | Failed/errors | Skipped | Expected failures |',
         '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
for name,row in rows.items():
    bad = sum(row[k] for k in ('failed','error','subtest_failure','unexpected_success','module_error'))
    lines.append(f"| {name} | {row['completed_files']}/{row['files']} | {row['declared_methods']} | {row['executed']} | {row['passed']} | {bad} | {row['skipped']} | {row['expected_failure']} |")
lines += ['', 'Missing shard summaries: '+str(missing),
          'Unfinished files: '+str(len(unexecuted)),
          'Module import/setup errors: '+str(len(module_errors)),
          '', 'Static method counts and runtime counts differ for inherited/parameterized tests; class-level setup errors and subtests are retained separately.',
          'See outcomes.json and each shard events.jsonl/tests.log for exact test IDs and errors.']
(root/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
raise SystemExit(0 if result['complete'] and not failures else 1)
