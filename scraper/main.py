"""Orchestrate fetch -> normalize/filter -> render.

  python -m scraper.main                 full run, writes index.html + data/
  python -m scraper.main --dry-run       fetch and filter, write nothing
  python -m scraper.main --only SLUG     restrict fetching to one source
  python -m scraper.main --offline       re-render from committed data only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import filters, lifecycle, render
from .adapters import get_adapter
from .registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "base.html"
DATA_DIR = ROOT / "data"
JOBS_PATH = DATA_DIR / "jobs.json"
HISTORY_PATH = DATA_DIR / "history.json"
UNRESOLVED_PATH = DATA_DIR / "unresolved.json"
INDEX_PATH = ROOT / "index.html"

FETCH_DELAY_SECONDS = 1


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def _log(message: str) -> None:
    print(message, flush=True)


def fetch_all(sources: list[dict], only: str | None, allowed_countries: list[str]) -> tuple[dict, dict, set]:
    """Fetch every source in sequence, isolating failures.

    Returns (normalized_by_slug, raw_counts, failed_slugs)."""
    normalized: dict[str, list[dict]] = {}
    raw_counts: dict[str, int] = {}
    failed: set[str] = set()
    wanted = [s for s in sources if only is None or s["slug"] == only]
    for i, source in enumerate(wanted):
        if i:
            time.sleep(FETCH_DELAY_SECONDS)
        slug = source["slug"]
        adapter = get_adapter(source["ats"])
        try:
            raw = adapter.fetch(source, allowed_countries)
            normalized[slug] = [adapter.normalize(r, source) for r in raw]
            raw_counts[slug] = len(raw)
            _log(f"  {slug}: {len(raw)} raw postings")
        except Exception as exc:  # one bad source must never abort the run
            failed.add(slug)
            _log(f"  {slug}: FAILED ({exc})")
    return normalized, raw_counts, failed


def build_meta(today: str, jobs: list[dict], failed: set[str]) -> dict:
    return {
        "generated": today,
        "failed_sources": sorted(failed),
        "total": len(jobs),
        "new": sum(1 for j in jobs if j["is_new"] and not j["stale"]),
    }


def summarize(jobs: list[dict], unresolved: list[dict], failed: set[str]) -> str:
    by_source: dict[str, int] = {}
    for job in jobs:
        slug = job["id"].split(":", 1)[0]
        by_source[slug] = by_source.get(slug, 0) + 1
    lines = ["", f"{'source':<28}{'kept':>6}"]
    for slug in sorted(set(by_source) | failed):
        note = "  FAILED" if slug in failed else ""
        lines.append(f"{slug:<28}{by_source.get(slug, 0):>6}{note}")
    lines.append(f"{'total':<28}{len(jobs):>6}")
    lines.append(f"unresolved locations: {len(unresolved)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scraper")
    parser.add_argument("--dry-run", action="store_true", help="fetch and filter, write nothing")
    parser.add_argument("--only", metavar="SLUG", help="fetch a single source")
    parser.add_argument("--offline", action="store_true", help="render from committed data, no network")
    args = parser.parse_args(argv)

    registry = load_registry(ROOT / "sources.yml")
    today = datetime.now(timezone.utc).date().isoformat()
    prev_jobs = _read_json(JOBS_PATH, [])
    history = _read_json(HISTORY_PATH, {})

    # If allowed_countries was narrowed since the last run, purge disallowed
    # rows immediately instead of letting them age out as stale.
    allowed = set(registry["allowed_countries"])
    prev_jobs = [j for j in prev_jobs if j.get("country") in allowed]

    if args.offline:
        meta = build_meta(today, prev_jobs, set())
        INDEX_PATH.write_text(
            render.render_page(TEMPLATE, prev_jobs, meta, registry["watch"]),
            encoding="utf-8", newline="\n",
        )
        _log(f"offline: rendered {INDEX_PATH.name} from {len(prev_jobs)} committed rows")
        return 0

    if args.only and args.only not in {s["slug"] for s in registry["sources"]}:
        _log(f"unknown source slug: {args.only}")
        return 2

    _log(f"fetching {len(registry['sources'])} sources...")
    normalized, raw_counts, failed = fetch_all(
        registry["sources"], args.only, registry["allowed_countries"]
    )

    current: dict[str, list[dict]] = {}
    unresolved: list[dict] = []
    for slug, rows in normalized.items():
        kept, unres = filters.apply_filters(rows, registry["allowed_countries"])
        current[slug] = kept
        unresolved.extend(unres)
    unresolved.sort(key=lambda u: u["id"])

    jobs, new_history, effective_failed = lifecycle.merge(
        current, raw_counts, failed, prev_jobs, history, today
    )

    _log(summarize(jobs, unresolved, effective_failed))

    if args.dry_run:
        _log("dry run: nothing written")
        return 0

    _write_json(JOBS_PATH, jobs)
    _write_json(HISTORY_PATH, new_history)
    _write_json(UNRESOLVED_PATH, unresolved)
    meta = build_meta(today, jobs, effective_failed)
    INDEX_PATH.write_text(
        render.render_page(TEMPLATE, jobs, meta, registry["watch"]),
        encoding="utf-8", newline="\n",
    )
    _log(f"wrote {INDEX_PATH.name}, data/jobs.json, data/history.json, data/unresolved.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
