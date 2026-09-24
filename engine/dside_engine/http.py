"""Polite JSON fetching with an on-disk cache.

Every public API we use is run by a small civic team, so the engine caches raw
responses and never asks for the same URL twice in one build. Pass
refresh=True (the --refresh flag) to ignore the cache and pull fresh data.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import httpx

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
USER_AGENT = "Masepala-engine/1.0 (+https://github.com/LeparaLaMapara/masepala)"


class Fetcher:
    def __init__(self, refresh: bool = False, retries: int = 4, timeout: float = 120.0):
        self.refresh = refresh
        self.retries = retries
        self.client = httpx.Client(
            timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        )
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
            except LookupError:
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"giving up on {url}: {last_error}")
