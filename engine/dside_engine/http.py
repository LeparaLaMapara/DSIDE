"""Polite JSON fetching with an on-disk cache, and the one HTTP client every source uses.

Every public API we use is run by a small civic team, so the engine caches raw
responses and never asks for the same URL twice in one build. Pass
refresh=True (the --refresh flag) to ignore the cache and pull fresh data.

Two rules live in client() so every download follows them:

* A host that stops answering is marked down for the rest of the run after
  DOWN_AFTER failures in a row. Later requests to it fail at once, so its
  sources fall back to their last good copy (snapshots.py) in seconds instead
  of waiting out every retry and timeout. Treasury's API going dark cost a
  whole 45 minute run before this.
* Some government sites only answer South African addresses (SASSA and DWS
  drop connections from abroad, including GitHub's runners). When
  DSIDE_ZA_RELAY is set, requests to those hosts go through the Masepala relay
  in Johannesburg (relay/), which fetches the page and passes it back.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import httpx

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
USER_AGENT = "Masepala-engine/1.0 (+https://github.com/ubunye-ai-ecosystems/masepala)"

CONNECT_TIMEOUT = 15.0
DOWN_AFTER = 3
# Hosts that refuse connections from outside South Africa (probed 2026-09-25:
# 39 of 40 foreign test points time out, Johannesburg answers in 0.2 s).
ZA_ONLY_HOSTS = {"sassa.gov.za", "www.sassa.gov.za", "ws.dws.gov.za"}

_failures: dict[str, int] = {}
DOWN: dict[str, str] = {}


class HostDown(httpx.ConnectError):
    """The host failed DOWN_AFTER times in a row; this run stops asking it."""


def reset() -> None:
    """Forget down hosts (tests, or a long-lived process starting a new run)."""
    _failures.clear()
    DOWN.clear()


def relay_url() -> str | None:
    return os.environ.get("DSIDE_ZA_RELAY", "").rstrip("/") or None


def za_only(host: str) -> bool:
    extra = {h.strip() for h in os.environ.get("DSIDE_ZA_ONLY_HOSTS", "").split(",") if h.strip()}
    return host in ZA_ONLY_HOSTS | extra


class GuardedTransport(httpx.HTTPTransport):
    """Sends a request, routing South Africa only hosts through the relay and tripping on dead hosts."""

    def __init__(self, verify: bool = True, **kwargs):
        super().__init__(verify=verify, **kwargs)
        self._relay_transport: httpx.HTTPTransport | None = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host in DOWN:
            raise HostDown(f"{host} is down for this run ({DOWN[host]})", request=request)
        try:
            response = self._send(request)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            _failures[host] = _failures.get(host, 0) + 1
            if _failures[host] >= DOWN_AFTER:
                DOWN[host] = f"{type(exc).__name__} {_failures[host]} times in a row"
                print(f"[down] {host}: {DOWN[host]}; its sources will use their last good copy")
            raise
        _failures[host] = 0
        return response

    def _send(self, request: httpx.Request) -> httpx.Response:
        relay = relay_url()
        if not (relay and za_only(request.url.host)):
            return super().handle_request(request)
        if self._relay_transport is None:
            self._relay_transport = httpx.HTTPTransport(verify=True)
        relayed = httpx.Request(
            "GET",
            f"{relay}/fetch",
            params={"url": str(request.url)},
            headers={
                "X-Relay-Token": os.environ.get("DSIDE_ZA_RELAY_TOKEN", ""),
                "User-Agent": request.headers.get("User-Agent", USER_AGENT),
            },
            extensions=request.extensions,
        )
        response = self._relay_transport.handle_request(relayed)
        response.request = request
        return response

    def close(self) -> None:
        if self._relay_transport is not None:
            self._relay_transport.close()
        super().close()


def client(timeout: float = 120.0, verify: bool = True, user_agent: str = USER_AGENT) -> httpx.Client:
    """The httpx client every download uses: short connect timeout, dead-host breaker, ZA relay."""
    return httpx.Client(
        timeout=httpx.Timeout(timeout, connect=min(CONNECT_TIMEOUT, timeout)),
        follow_redirects=True,
        headers={"User-Agent": user_agent},
        transport=GuardedTransport(verify=verify),
    )


class Fetcher:
    def __init__(self, refresh: bool = False, retries: int = 4, timeout: float = 120.0):
        self.refresh = refresh
        self.retries = retries
        self.client = client(timeout)
        CACHE_DIR.mkdir(exist_ok=True)
        self.log: list[dict] = []

    def _path(self, url: str) -> Path:
        return CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest() + ".json")

    def get(self, url: str) -> dict | list:
        path = self._path(url)
        if path.exists() and not self.refresh:
            return json.loads(path.read_text(encoding="utf-8"))
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                resp = self.client.get(url)
                if resp.status_code == 404:
                    raise LookupError(f"404 {url}")
                resp.raise_for_status()
                data = resp.json()
                path.write_text(json.dumps(data), encoding="utf-8")
                self.log.append({"url": url, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
                return data
            except (LookupError, HostDown):
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"giving up on {url}: {last_error}")
