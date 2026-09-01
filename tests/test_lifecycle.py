"""The 3-consecutive-misses rule and the never-regress-on-failure behaviour —
the easiest things here to get subtly wrong."""

from scraper.lifecycle import merge


def _row(job_id="acme:1", **overrides):
    row = {
        "id": job_id,
        "company": "Acme",
        "title": "FPGA Intern",
        "location_raw": "Toronto, ON, Canada",
        "country": "Canada",
        "city": "Toronto",
        "url": "https://x.test",
        "posted_at": None,
        "track": "Silicon & FPGA",
        "also_matched": [],
        "source": "greenhouse",
    }
    row.update(overrides)
    return row


def test_fresh_posting_gets_first_seen_today_and_is_new():
    jobs, history, failed = merge(
        current={"acme": [_row()]}, raw_counts={"acme": 1}, failed=set(),
        prev_jobs=[], history={}, today="2026-09-01",
    )
    (job,) = jobs
    assert job["first_seen"] == "2026-09-01"
    assert job["last_seen"] == "2026-09-01"
    assert job["is_new"] and not job["stale"]
    assert history["acme:1"] == {"first_seen": "2026-09-01", "last_seen": "2026-09-01", "misses": 0}
    assert failed == set()


def test_first_seen_is_stable_and_new_expires_after_seven_days():
    prev = [_row(first_seen="2026-08-20", last_seen="2026-08-31", is_new=True, stale=False)]
    history = {"acme:1": {"first_seen": "2026-08-20", "last_seen": "2026-08-31", "misses": 0}}
    jobs, new_history, _ = merge(
        current={"acme": [_row()]}, raw_counts={"acme": 1}, failed=set(),
        prev_jobs=prev, history=history, today="2026-09-01",
    )
    (job,) = jobs
    assert job["first_seen"] == "2026-08-20"   # never re-derived
    assert job["last_seen"] == "2026-09-01"
    assert not job["is_new"]                    # 12 days old


def test_three_consecutive_misses_then_gone():
    prev = [_row(first_seen="2026-08-01", last_seen="2026-08-28", is_new=False, stale=False)]
    history = {"acme:1": {"first_seen": "2026-08-01", "last_seen": "2026-08-28", "misses": 0}}
    # Source answers healthily (with other postings) but this id is absent.
    for day, expect_present, expect_misses in [
        ("2026-08-29", True, 1),
        ("2026-08-30", True, 2),
        ("2026-08-31", False, None),
    ]:
        other = _row("acme:2")
        jobs, history, _ = merge(
            current={"acme": [other]}, raw_counts={"acme": 5}, failed=set(),
            prev_jobs=prev, history=history, today=day,
        )
        carried = [j for j in jobs if j["id"] == "acme:1"]
        if expect_present:
            (job,) = carried
            assert job["stale"] is True
            assert job["last_seen"] == "2026-08-28"  # not bumped while absent
            assert history["acme:1"]["misses"] == expect_misses
        else:
            assert carried == []
            assert "acme:1" not in history
        prev = jobs


def test_reappearing_posting_resets_misses():
    prev = [_row(first_seen="2026-08-01", last_seen="2026-08-28", is_new=False, stale=True)]
    history = {"acme:1": {"first_seen": "2026-08-01", "last_seen": "2026-08-28", "misses": 2}}
    jobs, history, _ = merge(
        current={"acme": [_row()]}, raw_counts={"acme": 1}, failed=set(),
        prev_jobs=prev, history=history, today="2026-09-01",
    )
    (job,) = jobs
    assert job["stale"] is False
    assert history["acme:1"]["misses"] == 0
    assert job["first_seen"] == "2026-08-01"


def test_failed_source_carries_rows_without_counting_misses():
    prev = [_row(first_seen="2026-08-01", last_seen="2026-08-31", is_new=False, stale=False)]
    history = {"acme:1": {"first_seen": "2026-08-01", "last_seen": "2026-08-31", "misses": 0}}
    for day in ("2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"):
        jobs, history, failed = merge(
            current={}, raw_counts={}, failed={"acme"},
            prev_jobs=prev, history=history, today=day,
        )
        (job,) = jobs
        assert job["stale"] is True
        assert history["acme:1"]["misses"] == 0  # a broken source is not a closed role
        assert "acme" in failed
        prev = jobs


def test_zero_raw_results_after_nonzero_is_treated_as_failure():
    prev = [_row(first_seen="2026-08-01", last_seen="2026-08-31", is_new=False, stale=False)]
    history = {"acme:1": {"first_seen": "2026-08-01", "last_seen": "2026-08-31", "misses": 0}}
    jobs, history, failed = merge(
        current={"acme": []}, raw_counts={"acme": 0}, failed=set(),
        prev_jobs=prev, history=history, today="2026-09-01",
    )
    (job,) = jobs
    assert job["stale"] is True
    assert "acme" in failed
    assert history["acme:1"]["misses"] == 0


def test_zero_raw_results_with_no_previous_rows_is_fine():
    jobs, history, failed = merge(
        current={"acme": []}, raw_counts={"acme": 0}, failed=set(),
        prev_jobs=[], history={}, today="2026-09-01",
    )
    assert jobs == [] and history == {} and failed == set()


def test_output_is_deterministically_sorted():
    rows = {"zeta": [_row("zeta:1", company="Zeta")], "acme": [_row("acme:2"), _row("acme:1")]}
    jobs, _, _ = merge(
        current=rows, raw_counts={"zeta": 1, "acme": 2}, failed=set(),
        prev_jobs=[], history={}, today="2026-09-01",
    )
    assert [j["id"] for j in jobs] == ["acme:1", "acme:2", "zeta:1"]
