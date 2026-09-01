"""Workday CXS job feed.

POST https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
body: {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}

Paginated by offset until `total` is exhausted. `postedOn` is relative text
("Posted Today"), so posted_at is null for this ATS.

Large tenants (NVIDIA, Micron) list thousands of postings and Workday caps
some boards at 2000 results, which would silently hide rows. So the fetch is
scoped server-side with the board's own location facets: a probe request
returns the facet tree, and every facet value whose descriptor resolves to an
allowed country is applied. This narrows *fetch scope* only — the location
gate in scraper.filters remains the authority on what is kept. If a board
exposes no usable location facet, the whole board is fetched (capped).
"""

from __future__ import annotations

import re

from .. import http
from ..filters import resolve_location

PAGE_SIZE = 20
MAX_POSTINGS = 2000  # safety valve against a runaway `total`
MAX_DETAIL_LOOKUPS = 25  # per source, for "N Locations" rows
_N_LOCATIONS = re.compile(r"^\d+ Locations$")

# Country-level facets first; city-level "locations" only as a fallback.
LOCATION_FACET_PARAMS = [
    "locationCountry",
    "Location_Country",
    "locationHierarchy1",
    "locations",
]


def select_location_facet(facets: list, allowed_countries: list[str]) -> tuple[str, list[str]] | None:
    """Pick the most country-shaped location facet and the value ids whose
    descriptors resolve to an allowed country. Pure — unit-testable."""
    allowed = set(allowed_countries)
    found: dict[str, list[str]] = {}

    def walk(nodes):
        for node in nodes or []:
            param = node.get("facetParameter")
            values = node.get("values") or []
            if param in LOCATION_FACET_PARAMS:
                ids = []
                for v in values:
                    country, _city = resolve_location(v.get("descriptor") or "")
                    if country in allowed and v.get("id"):
                        ids.append(v["id"])
                if ids:
                    found.setdefault(param, []).extend(ids)
            for v in values:
                if v.get("facetParameter") or (v.get("values") and not v.get("id")):
                    walk([v])

    walk(facets)
    for param in LOCATION_FACET_PARAMS:
        if param in found:
            return param, found[param]
    return None


def _base_url(source: dict) -> str:
    return f"https://{source['tenant']}.{source['dc']}.myworkdayjobs.com"


def fetch(source: dict, allowed_countries: list[str] | None = None) -> list[dict]:
    url = f"{_base_url(source)}/wday/cxs/{source['tenant']}/{source['site']}/jobs"

    applied_facets: dict = {}
    if allowed_countries:
        probe = http.post_json(
            url, {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}
        )
        facet = select_location_facet(probe.get("facets") or [], allowed_countries)
        if facet:
            applied_facets = {facet[0]: facet[1]}

    postings: list[dict] = []
    offset = 0
    total = None
    while True:
        data = http.post_json(
            url,
            {"appliedFacets": applied_facets, "limit": PAGE_SIZE, "offset": offset, "searchText": ""},
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

    # A multi-location posting lists only "N Locations"; the job-detail
    # endpoint has the real list. Look those up (bounded) so the location
    # gate sees actual places instead of sending the row to unresolved.
    detail_base = f"{_base_url(source)}/wday/cxs/{source['tenant']}/{source['site']}"
    looked_up = 0
    for posting in postings:
        if not _N_LOCATIONS.fullmatch(posting.get("locationsText") or ""):
            continue
        if looked_up >= MAX_DETAIL_LOOKUPS:
            break
        looked_up += 1
        try:
            info = http.get_json(detail_base + posting.get("externalPath", "")).get("jobPostingInfo") or {}
        except http.FetchError:
            continue  # leave "N Locations" for the unresolved report
        places = [info.get("location") or ""] + list(info.get("additionalLocations") or [])
        places = [p for p in places if p]
        if places:
            posting["locationsText"] = "; ".join(places)
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
