"""Fresh local recovery inside the pinned image; settings arrive on stdin.

Only called for a new Compose project and volume, never an existing database.
The desktop validates a private snapshot, and this process validates it again.
"""
import json
import os
from pathlib import Path
import secrets
import sys
import time

from backup import inspect_backup, extract_attachments, read_json


def main():
    import frappe
    import pymysql
    from frappe.installer import _new_site, is_partial, is_downgrade, validate_database_sql

    settings = json.load(sys.stdin)
    source = Path('/run/nahj/backup')
    report = inspect_backup(source, settings['image'])
    os.chdir('/home/frappe/frappe-bench/sites')
    site = settings['site']
    if Path(site).exists():
        raise RuntimeError('Recovery target already exists; refusing to overwrite it.')
    sql = str(source / report['files']['database'])
    common = dict(db_host='db', db_port=3306, redis_cache='redis://redis-cache:6379',
                  redis_queue='redis://redis-queue:6379', redis_socketio='redis://redis-queue:6379',
                  socketio_port=9000, default_site=site, serve_default_site=True,
                  host_name=f"http://127.0.0.1:{settings['port']}",
                  chromium_path='/usr/lib/chromium/chromium-headless-shell',
                  pause_scheduler=True, mute_emails=True)
    Path('common_site_config.json').write_text(json.dumps(common))
    Path('common_site_config.json').chmod(0o600)
    Path('apps.txt').write_text('frappe\nerpnext\n')
    frappe.init(site, new_site=True, sites_path='.')
    frappe.conf.db_type = 'mariadb'
    # Preserve upstream database validation as well as our exact-image gate.
    if is_partial(sql) or is_downgrade(sql):
        raise RuntimeError('Partial backups and database downgrades are not supported.')
    validate_database_sql(sql)
    deadline = time.monotonic() + 180
    while True:
        try:
            connection = pymysql.connect(host='db', user='root', password=settings['password'], connect_timeout=10)
            connection.close()
            break
        except pymysql.OperationalError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)
    _new_site(db_name=None, site=site, db_type='mariadb', db_host='db', db_port=3306,
              db_root_username='root', db_root_password=settings['password'],
              admin_password=secrets.token_urlsafe(32), source_sql=sql,
              mariadb_user_host_login_scope='%')
    config_path = Path(site, 'site_config.json')
    config = read_json(config_path)
    original = read_json(source / report['files']['config'])
    for key in ('encryption_key', 'backup_encryption_key'):
        if key in original:
            config[key] = original[key]
    config.update(pause_scheduler=True, mute_emails=True, maintenance_mode=0)
    config_path.write_text(json.dumps(config))
    config_path.chmod(0o600)
    extract_attachments(source, site, report)
    frappe.destroy()
    frappe.init(site, sites_path='.')
    frappe.connect()
    if set(frappe.get_installed_apps()) != {'frappe', 'erpnext'}:
        raise RuntimeError('Backup requires additional applications. Recovery remains stopped for inspection.')
    frappe.db.set_single_value('System Settings', 'enable_scheduler', 0)
    frappe.db.commit()
    frappe.clear_cache()
    frappe.destroy()
    print('Recovery completed; automatic tasks and email remain paused for review.')


if __name__ == '__main__':
    main()
