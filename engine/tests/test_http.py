"""The shared HTTP client: dead hosts trip fast."""

import time

import httpx
import pytest

from dside_engine import http


@pytest.fixture(autouse=True)
def clean():
    http.reset()
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
