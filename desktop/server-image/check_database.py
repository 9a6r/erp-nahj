"""Read-only external MariaDB preflight. Credentials are read from stdin."""
import json
import re
import ssl
import sys


def check(settings):
    import pymysql

    context = ssl.create_default_context(cafile='/run/nahj/ca.pem')
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    with pymysql.connect(
        host=settings['host'], port=int(settings['port']), user=settings['user'],
        password=settings['password'], database=settings['database'],
        ssl=context, connect_timeout=10, read_timeout=15, write_timeout=15,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW SESSION STATUS LIKE 'Ssl_cipher'")
            row = cursor.fetchone()
            if not row or not row[1]:
                raise RuntimeError('MariaDB TLS is required.')
            cursor.execute('SELECT VERSION()')
            version = cursor.fetchone()[0]
            match = re.match(r'(\d+)\.(\d+)', version)
            if 'MariaDB' not in version or not match or tuple(map(int, match.groups())) < (10, 6):
                raise RuntimeError('MariaDB 10.6 or later is required.')
            cursor.execute('SHOW FULL TABLES')
            if cursor.fetchone():
                raise RuntimeError('External database is not empty; provisioning refused.')
    print('MariaDB TLS certificate, hostname, credentials, version and empty database verified.')


if __name__ == '__main__':
    check(json.load(sys.stdin))
