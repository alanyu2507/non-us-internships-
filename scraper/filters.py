"""The three gates: location, seniority, discipline.

Pure functions over the normalized schema — no network, no clock, no I/O.
Every keyword list is a module-level constant so it can be tuned without
reading the code around it.
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------
# Gate 1 — location. An explicit lookup table, not a regex guess.
# resolve_location() checks, in order: country aliases, US states/cities,
# Canadian provinces and other sub-national regions, then known cities.
# Anything that matches nothing is reported as unresolved, never guessed.
# --------------------------------------------------------------------------

US = "United States"

# lowercase alias -> canonical country name
COUNTRY_ALIASES = {
    "united states": US,
    "united states of america": US,
    "usa": US,
    "us": US,
    "u.s.": US,
    "u.s.a.": US,
    "estados unidos": US,
    "canada": "Canada",
    "china": "China",
    "mainland china": "China",
    "china mainland": "China",
    "people's republic of china": "China",
    "prc": "China",
    "hong kong": "Hong Kong",
    "hong kong sar": "Hong Kong",
    "hong kong s.a.r.": "Hong Kong",
    "hongkong": "Hong Kong",
    "taiwan": "Taiwan",
    "singapore": "Singapore",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "great britain": "United Kingdom",
    "england": "United Kingdom",
    "scotland": "United Kingdom",
    "wales": "United Kingdom",
    "northern ireland": "United Kingdom",
    "germany": "Germany",
    "deutschland": "Germany",
    "netherlands": "Netherlands",
    "the netherlands": "Netherlands",
    "holland": "Netherlands",
    "ireland": "Ireland",
    "israel": "Israel",
    "japan": "Japan",
    "south korea": "South Korea",
    "korea": "South Korea",
    "republic of korea": "South Korea",
    "korea, republic of": "South Korea",
    "australia": "Australia",
    # Countries that appear on multinational boards; resolved so they are
    # dropped by the allowed-countries gate instead of landing in unresolved.
    "france": "France",
    "india": "India",
    "poland": "Poland",
    "spain": "Spain",
    "italy": "Italy",
    "switzerland": "Switzerland",
    "sweden": "Sweden",
    "belgium": "Belgium",
    "austria": "Austria",
    "denmark": "Denmark",
    "norway": "Norway",
    "finland": "Finland",
    "portugal": "Portugal",
    "czech republic": "Czech Republic",
    "czechia": "Czech Republic",
    "romania": "Romania",
    "hungary": "Hungary",
    "mexico": "Mexico",
    "brazil": "Brazil",
    "argentina": "Argentina",
    "colombia": "Colombia",
    "costa rica": "Costa Rica",
    "vietnam": "Vietnam",
    "thailand": "Thailand",
    "malaysia": "Malaysia",
    "indonesia": "Indonesia",
    "philippines": "Philippines",
    "new zealand": "New Zealand",
    "united arab emirates": "United Arab Emirates",
    "uae": "United Arab Emirates",
    "saudi arabia": "Saudi Arabia",
    "turkey": "Turkey",
    "egypt": "Egypt",
    "south africa": "South Africa",
    "nigeria": "Nigeria",
    "kenya": "Kenya",
    "serbia": "Serbia",
    "croatia": "Croatia",
    "bulgaria": "Bulgaria",
    "slovakia": "Slovakia",
    "slovenia": "Slovenia",
    "lithuania": "Lithuania",
    "latvia": "Latvia",
    "estonia": "Estonia",
    "ukraine": "Ukraine",
    "greece": "Greece",
}

US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire",
    "new jersey", "new mexico", "new york", "north carolina", "north dakota",
    "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "west virginia", "wisconsin", "wyoming",
    "district of columbia", "puerto rico",
}

# Note: "ca" deliberately means California here — ATS strings write Canada
# out in full but abbreviate states ("San Jose, CA").
US_STATE_ABBREVS = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
    "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
    "wi", "wy", "dc", "pr",
}

US_PHRASES = {
    "remote - us", "remote us", "us remote", "remote - usa", "usa remote",
    "remote, us", "remote (us)", "us - remote", "anywhere in the us",
    "united states - remote", "remote united states",
}

US_CITIES = {
    "san francisco", "san jose", "santa clara", "sunnyvale", "mountain view",
    "palo alto", "cupertino", "fremont", "san diego", "los angeles", "irvine",
    "seattle", "bellevue", "redmond", "portland", "austin", "dallas",
    "houston", "phoenix", "chandler", "tempe", "denver", "boulder",
    "fort collins", "boston", "cambridge, ma", "new york city", "nyc",
    "chicago", "atlanta", "raleigh", "durham", "pittsburgh", "philadelphia",
    "detroit", "ann arbor", "minneapolis", "boise", "salt lake city",
    "colorado springs", "santa barbara", "folsom", "hillsboro", "allentown",
    "burlington, ma", "marlborough", "westford", "shrewsbury",
}

# lowercase sub-national region -> country
REGION_TO_COUNTRY = {
    # Canadian provinces
    "ontario": "Canada", "on": "Canada",
    "quebec": "Canada", "québec": "Canada", "qc": "Canada",
    "british columbia": "Canada", "bc": "Canada",
    "alberta": "Canada", "ab": "Canada",
    "manitoba": "Canada", "mb": "Canada",
    "saskatchewan": "Canada", "sk": "Canada",
    "nova scotia": "Canada", "ns": "Canada",
    "new brunswick": "Canada", "nb": "Canada",
    "newfoundland and labrador": "Canada", "nl": "Canada",
    "prince edward island": "Canada", "pe": "Canada",
    # Chinese provinces (Workday and Recruitee often emit "City, Province")
    "shaanxi": "China", "jiangsu": "China", "guangdong": "China",
    "zhejiang": "China", "sichuan": "China", "hubei": "China",
    "fujian": "China", "anhui": "China", "shandong": "China",
    "liaoning": "China", "hebei": "China", "hunan": "China",
    "henan": "China",
    # elsewhere
    "greater london": "United Kingdom",
    "bavaria": "Germany", "bayern": "Germany",
    "north holland": "Netherlands", "south holland": "Netherlands",
    "new south wales": "Australia", "nsw": "Australia",
    "victoria": "Australia", "vic": "Australia",
    "queensland": "Australia", "qld": "Australia",
}

# lowercase city -> country (only unambiguous names belong here)
CITY_TO_COUNTRY = {
    # Canada
    "toronto": "Canada", "markham": "Canada", "waterloo": "Canada",
    "kitchener": "Canada", "kitchener-waterloo": "Canada", "ottawa": "Canada",
    "montreal": "Canada", "montréal": "Canada", "vancouver": "Canada",
    "mississauga": "Canada", "brampton": "Canada", "edmonton": "Canada",
    "calgary": "Canada", "burnaby": "Canada", "halifax": "Canada",
    "quebec city": "Canada", "winnipeg": "Canada",
    "ste-anne-de-bellevue": "Canada", "sherbrooke": "Canada",
    # China
    "shanghai": "China", "beijing": "China", "shenzhen": "China",
    "suzhou": "China", "chengdu": "China", "xi'an": "China",
    "xian": "China", "xi an": "China",
    "hangzhou": "China", "nanjing": "China", "wuhan": "China",
    "guangzhou": "China", "tianjin": "China",
    # Taiwan
    "taipei": "Taiwan", "hsinchu": "Taiwan", "hsinchu city": "Taiwan",
    "taichung": "Taiwan",
    # United Kingdom
    "london": "United Kingdom", "cambridge": "United Kingdom",
    "bristol": "United Kingdom", "edinburgh": "United Kingdom",
    "manchester": "United Kingdom", "glasgow": "United Kingdom",
    "oxford": "United Kingdom",
    # Germany
    "munich": "Germany", "münchen": "Germany", "berlin": "Germany",
    "hamburg": "Germany", "dresden": "Germany", "stuttgart": "Germany",
    "frankfurt": "Germany", "cologne": "Germany", "nuremberg": "Germany",
    # Netherlands
    "amsterdam": "Netherlands", "eindhoven": "Netherlands",
    "delft": "Netherlands", "nijmegen": "Netherlands",
    "rotterdam": "Netherlands", "utrecht": "Netherlands",
    # Ireland
    "dublin": "Ireland", "cork": "Ireland", "limerick": "Ireland",
    "galway": "Ireland", "shannon": "Ireland",
    # Israel
    "tel aviv": "Israel", "tel aviv-yafo": "Israel", "haifa": "Israel",
    "jerusalem": "Israel", "herzliya": "Israel", "ra'anana": "Israel",
    "petah tikva": "Israel", "yokneam": "Israel",
    # Japan
    "tokyo": "Japan", "osaka": "Japan", "yokohama": "Japan", "kyoto": "Japan",
    "nagoya": "Japan", "fukuoka": "Japan",
    # South Korea
    "seoul": "South Korea", "pangyo": "South Korea", "suwon": "South Korea",
    "hwaseong": "South Korea", "pyeongtaek": "South Korea",
    # Australia
    "sydney": "Australia", "melbourne": "Australia", "brisbane": "Australia",
    "perth": "Australia", "adelaide": "Australia", "canberra": "Australia",
}

_ZIP_SUFFIX = re.compile(r"\s+\d{5}(-\d{4})?$")


def _tokens(raw: str) -> list[str]:
    # Split on commas/semicolons/pipes/slashes and on " - " (spaced hyphen,
    # so hyphenated names like Ste-Anne-de-Bellevue survive).
    parts = re.split(r"[,;|/]|\s-\s|[–—]", raw)
    tokens = []
    for part in parts:
        token = re.sub(r"\s+", " ", part).strip().strip(".").lower()
        token = _ZIP_SUFFIX.sub("", token)
        if token:
            tokens.append(token)
    return tokens


def resolve_location(location_raw: str) -> tuple[str | None, str]:
    """Return (country, city). country is None if unresolvable."""
    raw = (location_raw or "").strip()
    if not raw:
        return None, ""
    lowered = re.sub(r"\s+", " ", raw).lower()
    tokens = _tokens(raw)

    if lowered in US_PHRASES or any(t in US_PHRASES for t in tokens):
        return US, ""
    # An explicit country token beats every heuristic — "Costa Rica, San Jose"
    # must not trip over the US city table. Last match wins (most specific).
    country = None
    for t in tokens:
        if t in COUNTRY_ALIASES:
            country = COUNTRY_ALIASES[t]
    if country is None:
        # No explicit country: US state/city indicators decide next.
        for t in tokens:
            if t in US_STATE_NAMES or t in US_CITIES:
                return US, ""
            # Bare two-letter state abbrevs only count when another token
            # gives them context ("San Jose, CA") — a lone "on" is a word.
            if t in US_STATE_ABBREVS and len(tokens) > 1:
                return US, ""
    if country is None:
        for t in tokens:
            if t in REGION_TO_COUNTRY:
                country = REGION_TO_COUNTRY[t]
                break
    if country is None:
        for t in tokens:
            if t in CITY_TO_COUNTRY:
                country = CITY_TO_COUNTRY[t]
                break
    if country is None:
        return None, ""

    city = ""
    first = tokens[0]
    if first in CITY_TO_COUNTRY or (
        first not in COUNTRY_ALIASES
        and first not in REGION_TO_COUNTRY
        and first not in US_STATE_NAMES
    ):
        # Preserve the original casing of the first segment.
        city = re.split(r"[,;|/]|\s-\s|[–—]", raw)[0].strip()
    return country, city


# --------------------------------------------------------------------------
# Gate 2 — seniority. Internships and co-ops only, matched on title.
# --------------------------------------------------------------------------

SENIORITY_INCLUDE = [
    "intern", "internship", "co-op", "coop", "student", "new grad",
    "graduate program", "placement", "apprentice", "实习", "校招",
]
SENIORITY_EXCLUDE = [
    "manager", "director", "senior", "staff", "principal", "lead",
    "II", "III",
]


def _word_match(keyword: str, text: str) -> bool:
    if not keyword.isascii():
        return keyword in text  # CJK has no word boundaries
    return re.search(rf"(?<![\w-]){re.escape(keyword)}(?![\w-])", text, re.IGNORECASE) is not None


def is_internship(title: str) -> bool:
    if not any(_word_match(k, title) for k in SENIORITY_INCLUDE):
        return False
    if "intern" in title.lower():  # covers intern / internship / 实习-with-English
        return True
    return not any(_word_match(k, title) for k in SENIORITY_EXCLUDE)


# --------------------------------------------------------------------------
# Gate 3 — discipline. First matching track wins; the rest become
# secondary tags in `also_matched`.
# --------------------------------------------------------------------------

TRACK_KEYWORDS = [
    ("Silicon & FPGA", [
        "fpga", "rtl", "asic", "verilog", "systemverilog", "vhdl", "soc",
        "silicon", "physical design", "design verification", "dv", "uvm",
        "tapeout", "semiconductor", "chip",
    ]),
    ("Computer Architecture", [
        "computer architecture", "microarchitecture", "cpu", "gpu", "risc-v",
        "cache", "memory subsystem", "performance modeling",
    ]),
    ("Embedded & Firmware", [
        "firmware", "embedded", "rtos", "freertos", "bare metal",
        "device driver", "bsp", "microcontroller", "mcu", "arm cortex",
        "bootloader",
    ]),
    ("Hardware & PCB", [
        "hardware engineer", "pcb", "schematic", "altium", "signal integrity",
        "power electronics", "analog", "mixed-signal", "board bring-up",
        "hardware validation",
    ]),
    ("Robotics & Controls", [
        "robotics", "robot", "motion control", "control systems",
        "mechatronics", "ros", "ros2", "slam", "perception", "autonomy",
        "actuator", "motor control",
    ]),
]

TRACK_ORDER = [name for name, _ in TRACK_KEYWORDS]


def assign_track(title: str, description: str = "") -> tuple[str | None, list[str]]:
    haystack = f"{title}\n{description}"
    matched = [
        name
        for name, keywords in TRACK_KEYWORDS
        if any(_word_match(k, haystack) for k in keywords)
    ]
    if not matched:
        return None, []
    return matched[0], matched[1:]


# --------------------------------------------------------------------------
# The combined pipeline over normalized rows.
# --------------------------------------------------------------------------


def apply_filters(rows: list[dict], allowed_countries: list[str]) -> tuple[list[dict], list[dict]]:
    """Return (kept, unresolved).

    kept rows gain country/city/track/also_matched and lose `description`.
    unresolved entries record locations the resolver couldn't classify — but
    only for rows that pass the seniority and discipline gates, so the report
    contains exactly the postings where a resolver miss could cost a listing
    (the gates are conjunctive, so the kept set is unaffected by this order).
    """
    allowed = set(allowed_countries)
    kept, unresolved = [], []
    for row in rows:
        if not is_internship(row["title"]):
            continue
        track, also = assign_track(row["title"], row.get("description", ""))
        if track is None:
            continue
        country, city = resolve_location(row["location_raw"])
        if country is None:
            unresolved.append({
                "id": row["id"],
                "source": row["source"],
                "title": row["title"],
                "location_raw": row["location_raw"],
            })
            continue
        if country == US or country not in allowed:
            continue
        out = {k: v for k, v in row.items() if k != "description"}
        out.update({"country": country, "city": city, "track": track, "also_matched": also})
        kept.append(out)
    return kept, unresolved
