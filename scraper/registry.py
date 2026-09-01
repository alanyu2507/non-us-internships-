"""Load sources.yml.

The pipeline's only third-party dependency is `requests`, so instead of PyYAML
this module parses the deliberately constrained subset of YAML that
sources.yml is written in:

  - comments and blank lines
  - `key: [a, b, c]`               (flow list of scalars)
  - `key:` followed by             (list of flow mappings)
    `  - {k: v, k: v, ...}`

Values containing commas must be double-quoted. Anything outside this shape
raises, loudly, rather than being half-parsed.
"""

from __future__ import annotations

import re
from pathlib import Path


class RegistryError(ValueError):
    pass


def _split_flow(body: str) -> list[str]:
    """Split `a, b, "c, d"` on top-level commas, respecting double quotes."""
    parts, buf, in_quote = [], [], False
    for ch in body:
        if ch == '"':
            in_quote = not in_quote
            buf.append(ch)
        elif ch == "," and not in_quote:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if in_quote:
        raise RegistryError(f"unbalanced quote in: {body!r}")
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    return value


def _parse_mapping(body: str, line: str) -> dict[str, str]:
    mapping = {}
    for pair in _split_flow(body):
        key, sep, value = pair.partition(":")
        if not sep or not key.strip():
            raise RegistryError(f"bad key/value pair {pair!r} in line: {line!r}")
        mapping[key.strip()] = _scalar(value)
    return mapping


def parse_registry_text(text: str) -> dict:
    data: dict = {}
    current_list: str | None = None
    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        item = re.fullmatch(r"-\s*\{(.*)\}", stripped)
        if item:
            if current_list is None:
                raise RegistryError(f"line {lineno}: list item outside a list key")
            data[current_list].append(_parse_mapping(item.group(1), line))
            continue
        key, sep, value = stripped.partition(":")
        if not sep or not re.fullmatch(r"[A-Za-z_][\w-]*", key):
            raise RegistryError(f"line {lineno}: cannot parse: {line!r}")
        value = value.strip()
        if not value:
            data[key] = []
            current_list = key
        elif value.startswith("[") and value.endswith("]"):
            data[key] = [_scalar(v) for v in _split_flow(value[1:-1])]
            current_list = None
        else:
            data[key] = _scalar(value)
            current_list = None
    return data


REQUIRED_BY_ATS = {
    "greenhouse": ("board",),
    "lever": ("board",),
    "ashby": ("board",),
    "recruitee": ("board",),
    "workday": ("tenant", "dc", "site"),
}


def load_registry(path: Path) -> dict:
    data = parse_registry_text(path.read_text(encoding="utf-8"))
    if not data.get("allowed_countries"):
        raise RegistryError("sources.yml: missing allowed_countries")
    seen_slugs = set()
    for src in data.get("sources", []):
        for key in ("slug", "company", "ats"):
            if not src.get(key):
                raise RegistryError(f"source missing {key!r}: {src}")
        ats = src["ats"]
        if ats not in REQUIRED_BY_ATS:
            raise RegistryError(f"unknown ats {ats!r} for source {src['slug']}")
        for key in REQUIRED_BY_ATS[ats]:
            if not src.get(key):
                raise RegistryError(f"{ats} source {src['slug']} missing {key!r}")
        if src["slug"] in seen_slugs:
            raise RegistryError(f"duplicate slug {src['slug']!r}")
        seen_slugs.add(src["slug"])
    data.setdefault("sources", [])
    data.setdefault("watch", [])
    return data
