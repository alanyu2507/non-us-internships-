"""Posting lifecycle: first_seen tracking, staleness, and the
3-consecutive-misses removal rule.

Pure functions — the clock comes in as `today` (an ISO date string).

history.json maps id -> {first_seen, last_seen, misses}. `misses` counts
consecutive runs in which the posting's source answered but the posting was
absent; a source-level failure freezes its rows instead of counting misses.
"""

from __future__ import annotations

from datetime import date, timedelta

MAX_MISSES = 3
NEW_WINDOW_DAYS = 7


def _slug_of(job_id: str) -> str:
    return job_id.split(":", 1)[0]


def merge(
    current: dict[str, list[dict]],
    raw_counts: dict[str, int],
    failed: set[str],
    prev_jobs: list[dict],
    history: dict[str, dict],
    today: str,
) -> tuple[list[dict], dict[str, dict], set[str]]:
    """Combine this run's filtered rows with the previous run's state.

    current    slug -> filtered rows for sources that were fetched
    raw_counts slug -> raw (pre-filter) posting count for fetched sources
    failed     slugs whose fetch raised

    Returns (jobs, new_history, effective_failed) where effective_failed
    additionally contains sources that returned zero raw postings this run
    despite having rows on the board last run — treated as a flake, not as
    every posting closing at once.
    """
    prev_by_slug: dict[str, list[dict]] = {}
    for job in prev_jobs:
        prev_by_slug.setdefault(_slug_of(job["id"]), []).append(job)

    effective_failed = set(failed)
    for slug, count in raw_counts.items():
        if count == 0 and prev_by_slug.get(slug):
            effective_failed.add(slug)

    # Sources never fetched this run (e.g. --only) keep their rows untouched.
    fetched_ok = {slug for slug in current if slug not in effective_failed}

    today_date = date.fromisoformat(today)
    new_history: dict[str, dict] = {}
    jobs: list[dict] = []

    def is_new(first_seen: str) -> bool:
        return today_date - date.fromisoformat(first_seen) <= timedelta(days=NEW_WINDOW_DAYS)

    for slug in fetched_ok:
        seen_ids = set()
        for row in current[slug]:
            entry = history.get(row["id"], {})
            first_seen = entry.get("first_seen") or today
            job = dict(row)
            job.update({
                "first_seen": first_seen,
                "last_seen": today,
                "is_new": is_new(first_seen),
                "stale": False,
            })
            jobs.append(job)
            new_history[row["id"]] = {"first_seen": first_seen, "last_seen": today, "misses": 0}
            seen_ids.add(row["id"])
        # Postings that were on the board but are absent from a healthy fetch.
        for old in prev_by_slug.get(slug, []):
            if old["id"] in seen_ids:
                continue
            misses = history.get(old["id"], {}).get("misses", 0) + 1
            if misses >= MAX_MISSES:
                continue  # gone for real — drop it and its history
            job = dict(old)
            job.update({"is_new": is_new(job.get("first_seen", today)), "stale": True})
            jobs.append(job)
            new_history[old["id"]] = {
                "first_seen": old.get("first_seen", today),
                "last_seen": old.get("last_seen", today),
                "misses": misses,
            }

    # Failed (or unfetched) sources: never regress — carry rows frozen.
    carried_slugs = set(prev_by_slug) - fetched_ok
    for slug in carried_slugs:
        for old in prev_by_slug[slug]:
            job = dict(old)
            job.update({"is_new": is_new(job.get("first_seen", today)), "stale": True})
            jobs.append(job)
            entry = history.get(old["id"], {})
            new_history[old["id"]] = {
                "first_seen": entry.get("first_seen", old.get("first_seen", today)),
                "last_seen": entry.get("last_seen", old.get("last_seen", today)),
                "misses": entry.get("misses", 0),
            }

    jobs.sort(key=lambda j: (j["company"].lower(), j["id"]))
    return jobs, new_history, effective_failed
