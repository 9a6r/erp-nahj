"""Create only a new disposable test_site; never reuse company or recovery data."""
import json
import os
from pathlib import Path
import time

assert os.environ.get('NAHJ_DISPOSABLE_MODULE_TESTS') == '1'
os.chdir('/home/frappe/frappe-bench/sites')
assert not Path('test_site').exists(), 'Refusing to replace an existing site'
import pymysql
for attempt in range(90):
    try:
        db = pymysql.connect(host='db', user='root', password='disposable-ci-only')
        db.close()
        break
    except pymysql.OperationalError:
        if attempt == 89:
            raise
        time.sleep(2)
config = dict(db_host='db', redis_cache='redis://redis:6379/0', redis_queue='redis://redis:6379/1',
              redis_socketio='redis://redis:6379/1', host_name='http://test_site:8000',
              default_site='test_site', serve_default_site=True, developer_mode=1,
              mute_emails=1, chromium_path='/usr/lib/chromium/chromium-headless-shell')
Path('common_site_config.json').write_text(json.dumps(config))
Path('apps.txt').write_text('frappe\nerpnext\n')
import frappe
from frappe.installer import _new_site
frappe.init('test_site', new_site=True, sites_path='.')
_new_site(db_name=None, site='test_site', db_type='mariadb', db_host='db', db_root_username='root',
          db_root_password='disposable-ci-only', admin_password='disposable-ci-only',
          install_apps=['erpnext'], mariadb_user_host_login_scope='%')
p=Path('test_site/site_config.json'); conf=json.loads(p.read_text())
conf.update(allow_tests=True, nahj_disposable_test_site=True, mute_emails=1,
            host_name='http://test_site:8000', admin_password='disposable-ci-only',
            root_login='root', root_password='disposable-ci-only',
            auto_email_id='test@example.com', throttle_user_limit=100)
p.write_text(json.dumps(conf));p.chmod(0o600)
frappe.destroy()
print('PASS: fresh disposable ERPNext test site created')
