"""Lever postings API.

GET https://api.lever.co/v0/postings/{board}?mode=json
"""

from __future__ import annotations

from datetime import datetime, timezone

from .. import http


def fetch(source: dict) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{source['board']}?mode=json"
    data = http.get_json(url)
    if not isinstance(data, list):
        raise http.FetchError(f"unexpected Lever payload for {source['slug']}")
    return data


def normalize(raw: dict, source: dict) -> dict:
    categories = raw.get("categories") or {}
    created = raw.get("createdAt")
    posted_at = None
    if isinstance(created, (int, float)):
        posted_at = datetime.fromtimestamp(created / 1000, tz=timezone.utc).isoformat()
    return {
        "id": f"{source['slug']}:{raw['id']}",
        "company": source["company"],
        "title": raw.get("text") or "",
        "location_raw": categories.get("location") or raw.get("country") or "",
        "url": raw.get("hostedUrl") or raw.get("applyUrl") or "",
        "posted_at": posted_at,
        "source": "lever",
        "description": raw.get("descriptionPlain") or "",
    }
