"""Bounded, TLS-verified Frappe discovery. Never receives account credentials."""
import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from urllib.parse import urlsplit
from .config import server_url


class ConnectionFailure(Exception):
    pass


class SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(req.full_url)[:2] != urlsplit(newurl)[:2]:
            raise ConnectionFailure('redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def probe(value):
    origin = server_url(value)
    handlers = [SameOriginRedirect()]
    host = urlsplit(origin).hostname
    if host in ('localhost', '127.0.0.1', '::1') or host.endswith('.localhost'):
        handlers.append(ProxyHandler({}))
    request = Request(origin + '/api/method/ping', headers={'Accept': 'application/json'})
    try:
        with build_opener(*handlers).open(request, timeout=12) as response:
            payload = response.read(65537)
            if len(payload) > 65536 or json.loads(payload).get('message') != 'pong':
                raise ConnectionFailure('invalid')
    except HTTPError as error:
        code = error.code
        error.close()
        raise ConnectionFailure('access' if code in (401, 403) else 'offline') from None
    except URLError as error:
        raise ConnectionFailure('tls' if isinstance(error.reason, ssl.SSLError) else 'offline') from None
    except (json.JSONDecodeError, UnicodeError, AttributeError):
        raise ConnectionFailure('invalid') from None
    except (TimeoutError, OSError):
        raise ConnectionFailure('offline') from None
    return origin
