"""Exercise a real 0.3.1 backup on the candidate in separate rootless volumes."""
import json
from pathlib import Path
import sys

import full_stack as check
from nahj_desktop.server import IMAGE_ID, RELEASE, private_write

check.ROOT = Path.home() / 'nahj-upgrade-validation'


def source():
    # Invoked using the retained 0.3.1 manifest and its exact published archive.
    assert RELEASE['version'] == '0.3.1-rc1'
    check.ARCHIVE = Path.home() / 'legacy-server.tar.gz'
    _, _, backup = check.prepare_source()
    private_write(check.ROOT / 'source-backup.txt', str(backup))
    check.report('PASS: legacy image created real transactions and a verified backup')


def restore():
    assert RELEASE['version'] == '0.3.2-rc1'
    state = json.loads((check.ROOT / 'state.json').read_text())
    old = check.controller('original')
    assert old.profile()['image'] in RELEASE['restore_sources']
    assert old.profile()['image'] != IMAGE_ID
    # The new desktop must still start the old image without modifying its DB.
    old.start()
    check.verify(old, state)
    old.stop()
    target = check.controller('upgraded')
    target.restore((check.ROOT / 'source-backup.txt').read_text(),
                   {'mode': 'local', 'site': 'nahj-validation-upgraded.localhost', 'port': 18092,
                    'language': 'ar'}, str(check.ARCHIVE))
    assert target.profile()['project'] != old.profile()['project']
    assert target.profile()['recovery_pending']
    check.inside(target, '''import json,sys,os
from pathlib import Path
import frappe
site=json.load(sys.stdin)['site']
assert site=='nahj-validation-upgraded.localhost'
os.chdir('/home/frappe/frappe-bench/sites')
p=Path(site,'site_config.json');c=json.loads(p.read_text());c['nahj_disposable_test_site']=True
p.write_text(json.dumps(c));p.chmod(0o600)
frappe.init(site,sites_path='.');frappe.connect()
assert set(frappe.get_installed_apps())=={'frappe','payments','erpnext'}
assert frappe.conf.pause_scheduler and frappe.conf.mute_emails
frappe.get_doc({'doctype':'Payment Gateway','gateway':'Nahj Acceptance Gateway'}).insert()
frappe.db.commit();frappe.destroy()
''', {'site': target.profile()['site']})
    check.verify(target, state, pending=True)
    target.complete_recovery()
    check.verify(target, state)
    target.stop()
    old.start()
    check.verify(old, state)
    old.stop()
    check.report('PASS: old site unchanged; independent upgraded site retains business data, files, permissions and encryption and adds real Payments')


def after_reboot():
    state = json.loads((check.ROOT / 'state.json').read_text())
    for name in ('upgraded', 'original'):
        server = check.controller(name)
        server.start()
        check.verify(server, state)
        server.stop()
    check.report('PASS: both old and upgraded sites remain usable after a complete Zen reboot')


if __name__ == '__main__':
    {'source': source, 'restore': restore, 'after-reboot': after_reboot}[sys.argv[1]]()
