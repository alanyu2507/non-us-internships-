"""Each adapter's normalization, against fixture JSON captured from the real
endpoints (no network)."""

import json
from pathlib import Path

from scraper.adapters import ashby, greenhouse, lever, recruitee, workday

FIXTURES = Path(__file__).parent / "fixtures"

SCHEMA_KEYS = {"id", "company", "title", "location_raw", "url", "posted_at", "source", "description"}


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _check_common(rows, ats, slug):
    assert rows, "fixture produced no rows"
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "ids must be unique"
    for row in rows:
        assert set(row) == SCHEMA_KEYS
        assert row["source"] == ats
        assert row["id"].startswith(f"{slug}:")
        assert row["title"]
        assert row["url"].startswith("https://")


def test_greenhouse():
    src = {"slug": "tenstorrent-university", "company": "Tenstorrent", "ats": "greenhouse", "board": "tenstorrentuniversity"}
    rows = [greenhouse.normalize(j, src) for j in _load("greenhouse_tenstorrentuniversity.json")["jobs"]]
    _check_common(rows, "greenhouse", "tenstorrent-university")
    assert any("Toronto" in r["location_raw"] for r in rows)
    assert all(r["posted_at"] for r in rows)
    assert all("<" not in r["description"] for r in rows), "content must be de-HTMLed"


def test_lever():
    src = {"slug": "waabi", "company": "Waabi", "ats": "lever", "board": "waabi"}
    rows = [lever.normalize(j, src) for j in _load("lever_waabi.json")]
    _check_common(rows, "lever", "waabi")
    # createdAt is epoch-milliseconds; must come out ISO 8601
    assert all(r["posted_at"] and r["posted_at"][:4].isdigit() for r in rows)
    assert any(r["location_raw"] == "Toronto, ON" for r in rows)


def test_ashby():
    src = {"slug": "cohere", "company": "Cohere", "ats": "ashby", "board": "cohere"}
    rows = [ashby.normalize(j, src) for j in _load("ashby_cohere.json")["jobs"]]
    _check_common(rows, "ashby", "cohere")
    assert any(r["location_raw"] == "Canada" for r in rows)


def test_recruitee():
    src = {"slug": "huawei-canada", "company": "Huawei Canada", "ats": "recruitee", "board": "huaweicanada"}
    rows = [recruitee.normalize(j, src) for j in _load("recruitee_huaweicanada.json")["offers"]]
    _check_common(rows, "recruitee", "huawei-canada")
    # "2026-08-27 18:14:24 UTC" must become ISO 8601
    assert all(r["posted_at"] and "T" in r["posted_at"] and "UTC" not in r["posted_at"] for r in rows)
    assert any("Canada" in r["location_raw"] for r in rows)


def test_workday():
    src = {"slug": "altera", "company": "Altera", "ats": "workday", "tenant": "altera", "dc": "wd1", "site": "Altera"}
    rows = [workday.normalize(j, src) for j in _load("workday_altera.json")["jobPostings"]]
    _check_common(rows, "workday", "altera")
    for row in rows:
        assert row["url"].startswith("https://altera.wd1.myworkdayjobs.com/Altera/job/")
        assert row["posted_at"] is None  # Workday only exposes relative dates


def test_workday_id_is_requisition_id():
    src = {"slug": "altera", "company": "Altera", "ats": "workday", "tenant": "altera", "dc": "wd1", "site": "Altera"}
    raw = {"title": "FPGA Design Intern", "externalPath": "/job/Toronto-ON/FPGA-Design-Intern_R01234", "locationsText": "Toronto, ON, Canada", "bulletFields": ["R01234"]}
    assert workday.normalize(raw, src)["id"] == "altera:R01234"
