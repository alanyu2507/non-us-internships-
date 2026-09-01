from pathlib import Path

import pytest

from scraper.registry import RegistryError, load_registry, parse_registry_text

ROOT = Path(__file__).resolve().parents[1]


def test_real_sources_yml_loads():
    registry = load_registry(ROOT / "sources.yml")
    assert "Canada" in registry["allowed_countries"]
    slugs = [s["slug"] for s in registry["sources"]]
    assert "tenstorrent-university" in slugs
    assert len(slugs) == len(set(slugs))
    for src in registry["sources"]:
        if src["ats"] == "workday":
            assert src["tenant"] and src["dc"] and src["site"]
        else:
            assert src["board"]
    assert all(w["company"] and w["url"] for w in registry["watch"])


def test_parses_quoted_values_with_commas():
    data = parse_registry_text(
        'watch:\n  - {company: Foo, url: "https://x.test/a,b", note: "one, two"}\n'
    )
    assert data["watch"][0]["url"] == "https://x.test/a,b"
    assert data["watch"][0]["note"] == "one, two"


def test_url_colons_survive():
    data = parse_registry_text("sources:\n  - {slug: a, url: https://x.test/path}\n")
    assert data["sources"][0]["url"] == "https://x.test/path"


def test_flow_list():
    data = parse_registry_text("allowed_countries: [Canada, Hong Kong]\n")
    assert data["allowed_countries"] == ["Canada", "Hong Kong"]


def test_garbage_raises():
    with pytest.raises(RegistryError):
        parse_registry_text("sources:\n  - slug: block-style-not-supported\n")
