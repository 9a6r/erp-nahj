"""Executed inside the verified Frappe image, with private JSON on stdin."""
import json
import os
from pathlib import Path
import sys
import time


def main():
    import pymysql
    import frappe
    from frappe.installer import _new_site, install_app

    settings = json.load(sys.stdin)
    os.chdir('/home/frappe/frappe-bench/sites')
    site = settings['site']
    if (Path(site) / 'site_config.json').is_file():
        frappe.init(site, sites_path='.')
        frappe.connect()
        installed = frappe.get_installed_apps()
        if 'frappe' not in installed:
            raise RuntimeError('The base site installation is incomplete. Data was retained; restore or repair it before retrying.')
        if 'erpnext' not in installed:
            install_app('erpnext')
        finish(frappe, settings)
        return
    if Path(site).exists():
        raise RuntimeError('Site directory already exists; refusing to overwrite it.')
    if len(settings.get('admin_password', '')) < 12:
        raise RuntimeError('Enter an Administrator password of at least 12 characters to initialize the site.')
    external = settings['mode'] == 'external'
    host = settings['db_host'] if external else 'db'
    port = settings['db_port'] if external else 3306
    connection = dict(host=host, port=port, user=settings['db_user'] if external else 'root',
                      password=settings['password'], connect_timeout=10)
    common = dict(db_host=host, db_port=port, redis_cache='redis://redis-cache:6379',
                  redis_queue='redis://redis-queue:6379', redis_socketio='redis://redis-queue:6379',
                  socketio_port=9000, default_site=site, serve_default_site=True,
                  host_name=f"http://127.0.0.1:{settings['port']}",
                  chromium_path='/usr/lib/chromium/chromium-headless-shell')
    if external:
        connection.update(database=settings['db_name'],
                          ssl={'ca': '/run/nahj/database-ca.pem', 'check_hostname': True})
        common.update(db_ssl_ca='/run/nahj/database-ca.pem', db_ssl_check_hostname=True)
    deadline = time.monotonic() + 180
    while True:
        try:
            database = pymysql.connect(**connection)
            break
        except pymysql.OperationalError:
            if external or time.monotonic() >= deadline:
                raise
            time.sleep(2)
    with database:
        with database.cursor() as cursor:
            if external:
                cursor.execute("SHOW SESSION STATUS LIKE 'Ssl_cipher'")
                cipher = cursor.fetchone()
                if not cipher or not cipher[1]:
                    raise RuntimeError('MariaDB connection is not encrypted; provisioning refused.')
                cursor.execute('SHOW TABLES')
                if cursor.fetchall():
                    raise RuntimeError('External database is not empty; provisioning refused.')
    Path('common_site_config.json').write_text(json.dumps(common))
    Path('apps.txt').write_text('frappe\nerpnext\n')
    os.chmod('common_site_config.json', 0o600)
    frappe.init(site, new_site=True, sites_path='.')
    _new_site(
        db_name=settings['db_name'] if external else None, site=site,
        db_type='mariadb', db_host=host, db_port=port,
        db_user=settings['db_user'] if external else None,
        db_password=settings['password'] if external else None,
        db_root_username=None if external else 'root',
        db_root_password=None if external else settings['password'],
        admin_password=settings['admin_password'], install_apps=['erpnext'],
        setup_db=not external, mariadb_user_host_login_scope='%',
    )
    frappe.connect()
    finish(frappe, settings)


def finish(frappe, settings):
    from frappe.utils.scheduler import enable_scheduler
    enable_scheduler()
    frappe.db.set_value('User', 'Administrator', 'language', settings.get('language', 'ar'))
    frappe.db.commit()
    frappe.destroy()


if __name__ == '__main__':
    main()
