"""Masepala ZA relay: fetch a page from a government site that only answers South African addresses.

SASSA and the Department of Water and Sanitation drop connections from outside
South Africa, so GitHub's runners (in the United States) cannot reach them.
This service runs in Google Cloud's Johannesburg region, fetches the page and
passes it back. It is not an open proxy: it needs the shared token, and it only
fetches from the hosts in ALLOWED, redirects included.

    GET /fetch?url=<page>   header X-Relay-Token: <token>
    GET /health   (Cloud Run reserves /healthz)

Standard library only, so the container needs nothing installed.
"""

from __future__ import annotations

import hmac
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED = {"sassa.gov.za", "www.sassa.gov.za", "ws.dws.gov.za"}
UNVERIFIED_TLS = {"ws.dws.gov.za"}  # DWS serves an incomplete certificate chain
TOKEN = os.environ.get("RELAY_TOKEN", "")
MAX_BYTES = 200 * 1024 * 1024
TIMEOUT = 300
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Masepala-relay/1.0 (+https://github.com/ubunye-ai-ecosystems/masepala)"


def allowed(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    return parts.scheme in ("http", "https") and (parts.hostname or "") in ALLOWED


class StayOnAllowedHosts(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed(newurl):
            raise urllib.error.HTTPError(newurl, 403, "redirect leaves the allowed hosts", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, user_agent: str) -> tuple[int, str, bytes]:
    context = ssl._create_unverified_context() if urllib.parse.urlsplit(url).hostname in UNVERIFIED_TLS else None
    opener = urllib.request.build_opener(StayOnAllowedHosts, urllib.request.HTTPSHandler(context=context))
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with opener.open(request, timeout=TIMEOUT) as r:
            body = r.read(MAX_BYTES + 1)
            status, ctype = r.status, r.headers.get("Content-Type", "application/octet-stream")
    except urllib.error.HTTPError as exc:
        body, status, ctype = exc.read()[:MAX_BYTES], exc.code, exc.headers.get("Content-Type", "text/plain")
    if len(body) > MAX_BYTES:
        return 502, "text/plain", b"file larger than the relay passes on"
    return status, ctype, body


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - name set by BaseHTTPRequestHandler
        parts = urllib.parse.urlsplit(self.path)
        if parts.path == "/health":
            return self.reply(200, "text/plain", b"ok")
        if parts.path != "/fetch":
            return self.reply(404, "text/plain", b"not found")
        if not TOKEN or not hmac.compare_digest(self.headers.get("X-Relay-Token", ""), TOKEN):
            return self.reply(401, "text/plain", b"missing or wrong token")
        url = urllib.parse.parse_qs(parts.query).get("url", [""])[0]
        if not allowed(url):
            return self.reply(403, "text/plain", b"host not allowed")
        try:
            status, ctype, body = fetch(url, self.headers.get("User-Agent") or DEFAULT_UA)
        except Exception as exc:  # noqa: BLE001 - report any upstream failure as a bad gateway
            return self.reply(502, "text/plain", f"{type(exc).__name__}: {exc}".encode()[:500])
        self.reply(status, ctype, body)

    def reply(self, status: int, ctype: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # one short line per request, without the token
        print(f"{self.command} {urllib.parse.urlsplit(self.path).path} {args[1] if len(args) > 1 else ''}")


if __name__ == "__main__":
    ThreadingHTTPServer(("", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
