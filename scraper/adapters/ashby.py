"""Ashby posting API.

GET https://api.ashbyhq.com/posting-api/job-board/{board}
"""

from __future__ import annotations

from .. import http


def fetch(source: dict) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{source['board']}"
    data = http.get_json(url)
    return data.get("jobs", [])


def normalize(raw: dict, source: dict) -> dict:
    return {
        "id": f"{source['slug']}:{raw['id']}",
        "company": source["company"],
        "title": raw.get("title") or "",
        "location_raw": raw.get("location") or "",
        "url": raw.get("jobUrl") or raw.get("applyUrl") or "",
        "posted_at": raw.get("publishedAt"),
        "source": "ashby",
        "description": raw.get("descriptionPlain") or "",
    }
