"""Polite JSON fetching with an on-disk cache, and the one HTTP client every source uses.

Every public API we use is run by a small civic team, so the engine caches raw
responses and never asks for the same URL twice in one build. Pass
refresh=True (the --refresh flag) to ignore the cache and pull fresh data.

One rule lives in client() so every download follows it: a host that stops answering is marked down for the rest of the run after
  DOWN_AFTER failures in a row. Later requests to it fail at once, so its
  sources fall back to their last good copy (snapshots.py) in seconds instead
  of waiting out every retry and timeout. Treasury's API going dark cost a
  whole 45 minute run before this.

SASSA and DWS only answer South African addresses; they are fetched by the
South African runner (za-sources.yml), not here.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import httpx

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
USER_AGENT = "Masepala-engine/1.0 (+https://github.com/ubunye-ai-ecosystems/masepala)"

CONNECT_TIMEOUT = 15.0
DOWN_AFTER = 3

_failures: dict[str, int] = {}
DOWN: dict[str, str] = {}


class HostDown(httpx.ConnectError):
    """The host failed DOWN_AFTER times in a row; this run stops asking it."""


def reset() -> None:
    """Forget down hosts (tests, or a long-lived process starting a new run)."""
    _failures.clear()
    DOWN.clear()


class GuardedTransport(httpx.HTTPTransport):
    """Sends a request, tripping on dead hosts."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host in DOWN:
            raise HostDown(f"{host} is down for this run ({DOWN[host]})", request=request)
        try:
            response = super().handle_request(request)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            _failures[host] = _failures.get(host, 0) + 1
            if _failures[host] >= DOWN_AFTER:
                DOWN[host] = f"{type(exc).__name__} {_failures[host]} times in a row"
                print(f"[down] {host}: {DOWN[host]}; its sources will use their last good copy")
            raise
        _failures[host] = 0
        return response


def client(timeout: float = 120.0, verify: bool = True, user_agent: str = USER_AGENT) -> httpx.Client:
    """The httpx client every download uses: short connect timeout and a dead-host breaker."""
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
