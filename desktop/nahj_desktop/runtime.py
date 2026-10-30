"""Managed container entrypoint with a loopback bridge for server-side printing.

Frappe's canonical URL stays the desktop-visible URL (including emailed links).
Renderers in backend/worker containers reach that same URL through a listener
bound only to their own loopback interface and forwarded to the private frontend.
No host networking, certificate override or public proxy is used.
"""
import json
import os
from pathlib import Path
import select
import socket
import socketserver
import subprocess
import sys
from urllib.parse import urlsplit

BENCH = Path('/home/frappe/frappe-bench')


class PrintBridge(socketserver.BaseRequestHandler):
    destination = ('frontend', 8080)

    def handle(self):
        try:
            with socket.create_connection(self.destination, timeout=10) as upstream:
                streams = (self.request, upstream)
                for stream in streams:
                    stream.settimeout(60)
                while True:
                    readable, _, _ = select.select(streams, [], [], 60)
                    if not readable:
                        return
                    for source in readable:
                        data = source.recv(65536)
                        if not data:
                            return
                        (upstream if source is self.request else self.request).sendall(data)
        except (OSError, TimeoutError):
            # Do not log requests: they can contain session cookies or private data.
            return


class BridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 64


def bridge_port(config):
    url = urlsplit(config.get('host_name', ''))
    if url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost'):
        raise RuntimeError('Managed printing requires the configured local HTTP origin.')
    port = url.port or 80
    if not 1024 <= port <= 65535 or port == 8000:
        raise RuntimeError('The managed HTTP port must be unprivileged and different from backend port 8000.')
    return port


def main():
    args = sys.argv[1:]
    if args[:1] == ['--bridge-fd']:
        listener = socket.socket(fileno=int(args[1]))
        with BridgeServer(listener.getsockname(), PrintBridge, bind_and_activate=False) as server:
            server.socket.close()
            server.socket = listener
            server.serve_forever()
        return
    if not args:
        raise SystemExit('A service command is required.')
    renders_documents = 'gunicorn' in Path(args[0]).name or args[:2] in (['bench', 'worker'], ['bench', 'schedule'])
    if renders_documents:
        config = json.loads((BENCH / 'sites/common_site_config.json').read_text())
        # Bind before starting the application, so a conflicting port fails clearly.
        with BridgeServer(('127.0.0.1', bridge_port(config)), PrintBridge) as listener:
            subprocess.Popen([sys.executable, __file__, '--bridge-fd', str(listener.fileno())],
                             pass_fds=[listener.fileno()])
    os.execv('/home/frappe/entrypoint.sh', ['/home/frappe/entrypoint.sh', *args])


if __name__ == '__main__':
    main()
