"""The ZA relay only fetches from its allowed hosts and needs the token."""

import importlib.util
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("relay_main", Path(__file__).resolve().parents[2] / "relay" / "main.py")
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


def test_only_allowed_hosts():
    assert relay.allowed("https://www.sassa.gov.za/publications/statistical-reports")
    assert relay.allowed("https://ws.dws.gov.za/IRIS/releases/x.pdf")
    assert not relay.allowed("https://example.com/")
    assert not relay.allowed("https://sassa.gov.za.evil.example/")
    assert not relay.allowed("file:///etc/passwd")


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setattr(relay, "TOKEN", "t")
    monkeypatch.setattr(relay, "fetch", lambda url, ua: (200, "text/plain", b"page"))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), relay.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def status(url, token=None):
    req = urllib.request.Request(url, headers={"X-Relay-Token": token} if token else {})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""


def test_token_and_host_are_checked(server):
    page = "https://www.sassa.gov.za/x"
    assert status(f"{server}/fetch?url={page}")[0] == 401
    assert status(f"{server}/fetch?url={page}", "wrong")[0] == 401
    assert status(f"{server}/fetch?url=https://example.com/", "t")[0] == 403
    assert status(f"{server}/fetch?url={page}", "t") == (200, b"page")
    assert status(f"{server}/health")[0] == 200
