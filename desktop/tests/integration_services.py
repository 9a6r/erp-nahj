"""Disposable-site checks of real SMTP delivery and signed webhook dispatch.

Receivers bind container loopback only. No email or webhook leaves the machine.
Requires the real Frappe worker and the explicit disposable-site configuration.
Run from sites/ with the bench Python and NAHJ_ACCEPTANCE_SITE set.
"""
import base64
from email import policy
from email.parser import BytesParser
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import secrets
import socketserver
import threading
import time

import frappe


class SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(30)
        self.wfile.write(b'220 nahj-validation ESMTP\r\n')
        while line := self.rfile.readline():
            command = line.split(b' ', 1)[0].strip().upper()
            if command in (b'EHLO', b'HELO'):
                self.wfile.write(b'250-nahj-validation\r\n250 SIZE 1048576\r\n')
            elif command in (b'MAIL', b'RCPT', b'RSET', b'NOOP'):
                self.wfile.write(b'250 OK\r\n')
            elif command == b'DATA':
                self.wfile.write(b'354 End with dot\r\n')
                content = bytearray()
                while data := self.rfile.readline():
                    if data == b'.\r\n':
                        break
                    content.extend(data[1:] if data.startswith(b'..') else data)
                    if len(content) > 1048576:
                        raise RuntimeError('Test message exceeded its size limit')
                self.server.messages.append(bytes(content))
                self.wfile.write(b'250 Queued by validation receiver\r\n')
            elif command == b'QUIT':
                self.wfile.write(b'221 Bye\r\n')
                break
            else:
                self.wfile.write(b'502 Unsupported\r\n')


class SMTPReceiver(socketserver.ThreadingTCPServer):
    daemon_threads = True


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        size = int(self.headers.get('Content-Length', 0))
        if size > 1048576:
            self.send_error(413)
            return
        body = self.rfile.read(size)
        self.server.events.append((body, self.headers.get('X-Frappe-Webhook-Signature')))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{}')

    def log_message(self, *_):
        pass


def main():
    site = os.environ.get('NAHJ_ACCEPTANCE_SITE', '')
    if site not in ('nahj.localhost', 'nahj-recovery.localhost') and not site.startswith('nahj-validation'):
        raise RuntimeError('An explicitly named disposable acceptance site is required.')
    frappe.init(site, sites_path='.')
    if not frappe.conf.get('nahj_disposable_test_site'):
        raise RuntimeError('Refusing to configure integration fixtures on a non-disposable site.')
    frappe.connect()
    frappe.set_user('Administrator')
    assert not frappe.are_emails_muted(), 'Activate the disposable recovery site before this test'
    smtp = SMTPReceiver(('127.0.0.1', 0), SMTPHandler)
    smtp.messages = []
    receiver = ThreadingHTTPServer(('127.0.0.1', 0), WebhookHandler)
    receiver.events = []
    for service in (smtp, receiver):
        threading.Thread(target=service.serve_forever, daemon=True).start()
    suffix = secrets.token_hex(6)
    email = f'nahj-{suffix}@example.test'
    account = webhook = None
    try:
        account = frappe.get_doc(dict(doctype='Email Account', email_account_name='Nahj validation ' + suffix,
            email_id=email, enable_outgoing=1, default_outgoing=1, smtp_server='127.0.0.1',
            smtp_port=smtp.server_address[1], use_tls=0, use_ssl_for_outgoing=0,
            no_smtp_authentication=1)).insert()
        frappe.db.commit()
        frappe.sendmail(recipients=['recipient@example.test'], sender=email,
                        subject='اختبار بريد نهج ' + suffix, message='وصلت الرسالة العربية بنجاح', now=True)
        # Frappe 16 sends even `now=True` after transaction commit.
        frappe.db.commit()
        assert len(smtp.messages) == 1
        message = BytesParser(policy=policy.default).parsebytes(smtp.messages[0])
        assert str(message['Subject']) == 'اختبار بريد نهج ' + suffix
        assert 'recipient@example.test' in str(message['To'])
        assert 'وصلت الرسالة العربية بنجاح' in message.get_body(preferencelist=('html', 'plain')).get_content()
        print('PASS: real Frappe Email Account delivered an Arabic MIME message over SMTP to loopback', flush=True)

        secret = secrets.token_urlsafe(32)
        webhook = frappe.get_doc(dict(doctype='Webhook', name='Nahj validation ' + suffix,
            webhook_doctype='ToDo', webhook_docevent='after_insert', enabled=1,
            request_url=f'http://127.0.0.1:{receiver.server_port}/hook', request_method='POST',
            request_structure='JSON', webhook_json='{"name": {{ doc.name | tojson }}, "description": {{ doc.description | tojson }}}',
            enable_security=1, webhook_secret=secret)).insert()
        frappe.db.commit()
        todo = frappe.get_doc(dict(doctype='ToDo', description='اختبار تكامل نهج ' + suffix,
                                  allocated_to='Administrator')).insert()
        frappe.db.commit()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not receiver.events:
            time.sleep(0.2)
        assert receiver.events, 'No real after_insert webhook was received'
        raw, signature = receiver.events[0]
        expected = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
        assert hmac.compare_digest(signature, expected)
        payload = json.loads(raw)
        assert payload['name'] == todo.name and payload['description'] == todo.description
        print('PASS: real document event and worker sent an Arabic webhook with a valid HMAC signature', flush=True)
    finally:
        if webhook:
            frappe.db.set_value('Webhook', webhook.name, 'enabled', 0)
            frappe.client_cache.delete_value('webhooks')
        if account:
            frappe.db.set_value('Email Account', account.name, {'enable_outgoing': 0, 'default_outgoing': 0})
        frappe.db.commit()
        for service in (smtp, receiver):
            service.shutdown()
            service.server_close()
        frappe.destroy()


if __name__ == '__main__':
    main()
