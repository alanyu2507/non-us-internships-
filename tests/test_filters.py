import pytest

from scraper.filters import (
    US,
    apply_filters,
    assign_track,
    is_internship,
    resolve_location,
)

# --------------------------------------------------------------------------
# Country resolver
# --------------------------------------------------------------------------

RESOLVER_CASES = [
    ("Toronto, ON, Canada", "Canada"),
    ("Waterloo, Ontario, Canada", "Canada"),
    ("Toronto, ON", "Canada"),
    ("Markham, Ontario", "Canada"),
    ("Ste-Anne-de-Bellevue, QC", "Canada"),
    ("Remote - Canada", "Canada"),
    ("Shanghai, China", "China"),
    ("Shenzhen", "China"),
    ("Hong Kong SAR", "Hong Kong"),
    ("Hong Kong", "Hong Kong"),
    ("London, UK", "United Kingdom"),
    ("London", "United Kingdom"),         # bare London defaults to UK...
    ("London, Ontario", "Canada"),        # ...but the province wins
    ("Cambridge, United Kingdom", "United Kingdom"),
    ("Munich, Germany", "Germany"),
    ("Tel Aviv, Israel", "Israel"),
    ("Singapore", "Singapore"),
    ("Tokyo, Japan", "Japan"),
    ("Seoul, South Korea", "South Korea"),
    ("Sydney, Australia", "Australia"),
    ("Austin, Texas, United States", US),
    ("Remote - US", US),
    ("Remote US", US),
    ("San Jose, CA", US),                 # CA reads as California, not Canada
    ("Cambridge, MA", US),                # Cambridge alone would be UK
    ("Virtual - Los Angeles, CA 90011", US),
    ("New York", US),
    ("Santa Clara, California, United States of America", US),
]


@pytest.mark.parametrize("raw,expected", RESOLVER_CASES)
def test_resolve_country(raw, expected):
    country, _city = resolve_location(raw)
    assert country == expected


@pytest.mark.parametrize("raw", ["", "Remote", "Flexible", "2 Locations", "EMEA"])
def test_unresolvable_stays_unresolved(raw):
    country, _city = resolve_location(raw)
    assert country is None


def test_city_extraction():
    assert resolve_location("Toronto, ON, Canada") == ("Canada", "Toronto")
    assert resolve_location("Canada")[1] == ""  # bare country has no city


# --------------------------------------------------------------------------
# Seniority
# --------------------------------------------------------------------------

SHOULD_MATCH = [
    "RTL Design Intern",
    "Hardware Engineering Internship - Summer 2027",
    "Firmware Co-op",
    "Engineering Coop, Robotics",
    "Design Verification Engineer, Intern",
    "Working Student, FPGA",
    "New Grad Silicon Engineer",
    "Graduate Program - Electronics",
    "Industrial Placement, Embedded Software",
    "Hardware Apprentice",
    "硬件实习生",
    "Senior Design Intern",     # senior... but intern is present
    "Staff Engineer Intern",    # ditto
]

SHOULD_NOT_MATCH = [
    "Senior Firmware Engineer",
    "Staff RTL Designer",
    "Principal Hardware Architect",
    "Engineering Manager, Robotics",
    "Director of Silicon Engineering",
    "Lead Embedded Developer",
    "Hardware Engineer II",
    "Design Engineer III",
    "Internal Sales Representative",   # 'internal' is not 'intern'
    "International Logistics Coordinator",
    "FPGA Design Engineer",            # no seniority signal either way
]


@pytest.mark.parametrize("title", SHOULD_MATCH)
def test_seniority_keeps(title):
    assert is_internship(title)


@pytest.mark.parametrize("title", SHOULD_NOT_MATCH)
def test_seniority_drops(title):
    assert not is_internship(title)


# --------------------------------------------------------------------------
# Discipline / track assignment
# --------------------------------------------------------------------------

def test_first_track_in_table_order_wins():
    track, also = assign_track("FPGA Robotics Intern", "")
    assert track == "Silicon & FPGA"
    assert also == ["Robotics & Controls"]


def test_description_counts():
    track, _ = assign_track("Engineering Intern", "You will write firmware for ARM Cortex MCUs")
    assert track == "Embedded & Firmware"


def test_no_track_means_none():
    assert assign_track("Marketing Intern", "social media campaigns") == (None, [])


def test_keywords_are_whole_words():
    # 'dv' must not fire inside other words, 'chip' not inside 'chipotle' etc.
    assert assign_track("Advertising Intern", "advisory services")[0] is None


# --------------------------------------------------------------------------
# The combined pipeline
# --------------------------------------------------------------------------

def _row(**overrides):
    row = {
        "id": "src:1",
        "company": "Acme",
        "title": "FPGA Intern",
        "location_raw": "Toronto, ON, Canada",
        "url": "https://x.test",
        "posted_at": None,
        "source": "greenhouse",
        "description": "",
    }
    row.update(overrides)
    return row


ALLOWED = ["Canada", "China", "Hong Kong", "United Kingdom"]


def test_pipeline_keeps_and_annotates():
    kept, unresolved = apply_filters([_row()], ALLOWED)
    assert not unresolved
    (job,) = kept
    assert job["country"] == "Canada"
    assert job["city"] == "Toronto"
    assert job["track"] == "Silicon & FPGA"
    assert "description" not in job


def test_pipeline_drops_us():
    kept, unresolved = apply_filters([_row(location_raw="Austin, Texas, United States")], ALLOWED)
    assert kept == [] and unresolved == []


def test_pipeline_drops_disallowed_country():
    kept, unresolved = apply_filters([_row(location_raw="Bangalore, India")], ALLOWED)
    assert kept == [] and unresolved == []


def test_pipeline_reports_unresolved_only_for_relevant_rows():
    rows = [
        _row(id="src:a", location_raw="Somewhere Odd"),
        _row(id="src:b", title="Senior Sales Manager", location_raw="Somewhere Odd"),
    ]
    kept, unresolved = apply_filters(rows, ALLOWED)
    assert kept == []
    assert [u["id"] for u in unresolved] == ["src:a"]
