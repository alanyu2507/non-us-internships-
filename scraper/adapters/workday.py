"""Workday CXS job feed.

POST https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
body: {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}

Paginated by offset until `total` is exhausted. `postedOn` is relative text
("Posted Today"), so posted_at is null for this ATS.
"""

from __future__ import annotations

from .. import http

PAGE_SIZE = 20
MAX_POSTINGS = 2000  # safety valve against a runaway `total`


def _base_url(source: dict) -> str:
    return f"https://{source['tenant']}.{source['dc']}.myworkdayjobs.com"


def fetch(source: dict) -> list[dict]:
    url = f"{_base_url(source)}/wday/cxs/{source['tenant']}/{source['site']}/jobs"
    postings: list[dict] = []
    offset = 0
    total = None
    while True:
        data = http.post_json(
            url,
            {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": ""},
        )
        page = data.get("jobPostings") or []
        postings.extend(page)
        if total is None:
            # Some tenants (e.g. Marvell) report total only on the first
            # page and 0 afterwards — trust the first answer.
            total = min(int(data.get("total") or 0), MAX_POSTINGS)
        offset += PAGE_SIZE
        if offset >= total or not page:
            break
    return postings


def normalize(raw: dict, source: dict) -> dict:
    path = raw.get("externalPath") or ""
    # The requisition id is the stable part: ".../Some-Title_R02998" -> R02998.
    req_id = path.rsplit("_", 1)[-1] if "_" in path else ""
    if not req_id:
        bullets = raw.get("bulletFields") or []
        req_id = bullets[0] if bullets else path
    return {
        "id": f"{source['slug']}:{req_id}",
        "company": source["company"],
        "title": raw.get("title") or "",
        "location_raw": raw.get("locationsText") or "",
        "url": f"{_base_url(source)}/{source['site']}{path}",
        "posted_at": None,
        "source": "workday",
        "description": "",
    }
