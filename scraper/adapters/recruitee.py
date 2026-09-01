"""Recruitee offers API.

GET https://{board}.recruitee.com/api/offers/
"""

from __future__ import annotations

import re

from .. import http
from . import strip_html


def fetch(source: dict) -> list[dict]:
    url = f"https://{source['board']}.recruitee.com/api/offers/"
    data = http.get_json(url)
    return data.get("offers", [])


def _iso(timestamp: str | None) -> str | None:
    # Recruitee emits "2026-08-27 18:14:24 UTC".
    if not timestamp:
        return None
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) UTC", timestamp)
    if match:
        return f"{match.group(1)}T{match.group(2)}+00:00"
    return timestamp


def normalize(raw: dict, source: dict) -> dict:
    location = raw.get("location") or ", ".join(
        part for part in (raw.get("city"), raw.get("country")) if part
    )
    description = strip_html(raw.get("description"))
    requirements = strip_html(raw.get("requirements"))
    return {
        "id": f"{source['slug']}:{raw['id']}",
        "company": source["company"],
        "title": raw.get("title") or "",
        "location_raw": location,
        "url": raw.get("careers_url") or raw.get("careers_apply_url") or "",
        "posted_at": _iso(raw.get("published_at")),
        "source": "recruitee",
        "description": f"{description} {requirements}".strip(),
    }
