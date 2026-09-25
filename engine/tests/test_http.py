"""The shared HTTP client: dead hosts trip fast, South Africa only hosts go through the relay."""

import time

import httpx
import pytest

from dside_engine import http


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    http.reset()
    monkeypatch.delenv("DSIDE_ZA_RELAY", raising=False)
    monkeypatch.delenv("DSIDE_ZA_RELAY_TOKEN", raising=False)
    yield
    http.reset()


def fake_network(monkeypatch, answer):
    """Replace the socket layer; answer(request) returns a Response or raises."""
    seen = []

    def handle(self, request):
        seen.append(request)
        return answer(request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    return seen


def test_a_dead_host_is_marked_down_and_then_fails_at_once(monkeypatch):
    def timeout(request):
        raise httpx.ConnectTimeout("timed out", request=request)

    seen = fake_network(monkeypatch, timeout)
    with http.client() as c:
        for _ in range(http.DOWN_AFTER):
            with pytest.raises(httpx.ConnectTimeout):
                c.get("https://municipaldata.treasury.gov.za/api/cubes")
        start = time.monotonic()
        with pytest.raises(http.HostDown):
            c.get("https://municipaldata.treasury.gov.za/api/other")
    assert time.monotonic() - start < 0.5
    assert len(seen) == http.DOWN_AFTER  # the last request never reached the network
    assert "municipaldata.treasury.gov.za" in http.DOWN


def test_a_success_resets_the_count(monkeypatch):
    calls = iter([httpx.ConnectTimeout, httpx.ConnectTimeout, None, httpx.ConnectTimeout, httpx.ConnectTimeout])

    def flaky(request):
        exc = next(calls)
        if exc:
            raise exc("slow", request=request)
        return httpx.Response(200, json={})

    fake_network(monkeypatch, flaky)
    with http.client() as c:
        for _ in range(5):
            try:
                c.get("https://api.wazimap.com/x")
            except httpx.ConnectTimeout:
                pass
    assert http.DOWN == {}


def test_fetcher_does_not_retry_a_down_host(monkeypatch):
    http.DOWN["municipaldata.treasury.gov.za"] = "test"
    monkeypatch.setattr(http.time, "sleep", lambda s: pytest.fail("should not wait on a down host"))
    with pytest.raises(http.HostDown):
        http.Fetcher(refresh=True).get("https://municipaldata.treasury.gov.za/api/cubes")


def test_za_only_hosts_go_through_the_relay(monkeypatch):
    monkeypatch.setenv("DSIDE_ZA_RELAY", "https://relay.example/")
    monkeypatch.setenv("DSIDE_ZA_RELAY_TOKEN", "secret")
    seen = fake_network(monkeypatch, lambda r: httpx.Response(200, content=b"%PDF"))
    with http.client() as c:
        r = c.get("https://www.sassa.gov.za/publications/statistical-reports")
        c.get("https://api.wazimap.com/x")
    assert r.content == b"%PDF"
    assert str(r.request.url) == "https://www.sassa.gov.za/publications/statistical-reports"
    relayed, direct = seen
    assert relayed.url.host == "relay.example" and relayed.url.path == "/fetch"
    assert relayed.url.params["url"] == "https://www.sassa.gov.za/publications/statistical-reports"
    assert relayed.headers["X-Relay-Token"] == "secret"
    assert direct.url.host == "api.wazimap.com"


def test_without_a_relay_za_hosts_are_asked_directly(monkeypatch):
    seen = fake_network(monkeypatch, lambda r: httpx.Response(200))
    with http.client() as c:
        c.get("https://ws.dws.gov.za/IRIS/latestresults.aspx")
    assert seen[0].url.host == "ws.dws.gov.za"
