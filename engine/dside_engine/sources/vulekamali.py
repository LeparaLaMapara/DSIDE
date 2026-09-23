"""Vulekamali (National Treasury) provincial and national infrastructure projects.

The old CKAN API is gone; the site's own search API still serves every
geolocated project (schools, clinics, housing, roads).
"""

from __future__ import annotations

from ..http import Fetcher

SEARCH = "https://vulekamali.gov.za/provincial-infrastructure/api/v1/infrastructure-projects/full/search/"
SITE = "https://vulekamali.gov.za"


def projects(f: Fetcher, page_size: int = 1000) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        data = f.get(f"{SEARCH}?limit={page_size}&offset={offset}")
        rows += data["results"]
        offset += page_size
        if offset >= data["count"] or not data["results"]:
            return rows
