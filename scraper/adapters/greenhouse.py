"""Greenhouse job boards API.

GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
"""

from __future__ import annotations

from .. import http
from . import strip_html


def fetch(source: dict) -> list[dict]:
    url = (
        "https://boards-api.greenhouse.io/v1/boards/"
        f"{source['board']}/jobs?content=true"
    )
    data = http.get_json(url)
    return data.get("jobs", [])


def normalize(raw: dict, source: dict) -> dict:
    location = (raw.get("location") or {}).get("name") or ""
    return {
        "id": f"{source['slug']}:{raw['id']}",
        "company": source["company"],
        "title": raw.get("title") or "",
        "location_raw": location,
        "url": raw.get("absolute_url") or "",
        "posted_at": raw.get("first_published") or raw.get("updated_at"),
        "source": "greenhouse",
        "description": strip_html(raw.get("content")),
    }
