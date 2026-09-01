"""One adapter per ATS.

Each adapter module exposes:

  fetch(source) -> list[dict]        raw postings, verbatim from the API
  normalize(raw, source) -> dict     one raw posting -> the flat schema

Adapters never filter — every posting the ATS returns comes back, and the
location/seniority/discipline gates in scraper.filters decide what survives.

normalize() returns the schema fields an adapter can know:
  id, company, title, location_raw, url, posted_at, source
plus a transient `description` (plain text, used only for the discipline
match and dropped before anything is written to disk).
"""

from __future__ import annotations

import html
import re


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_adapter(ats: str):
    from . import ashby, greenhouse, lever, recruitee, workday

    return {
        "greenhouse": greenhouse,
        "lever": lever,
        "ashby": ashby,
        "recruitee": recruitee,
        "workday": workday,
    }[ats]
