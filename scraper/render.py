"""Render index.html from the filtered dataset.

templates/base.html is the finished design; this module only fills its three
JSON slots. Output is deterministic for a given (jobs, meta, watch) input.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_SLOT = "/*__DATA__*/[]"
META_SLOT = '/*__META__*/{"generated":"","failed_sources":[]}'
WATCH_SLOT = "/*__WATCH__*/[]"


def _json(value) -> str:
    # `</` must not appear verbatim inside an inline <script>.
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).replace("</", "<\\/")


def render_page(template_path: Path, jobs: list[dict], meta: dict, watch: list[dict]) -> str:
    html = template_path.read_text(encoding="utf-8")
    for slot, value in ((DATA_SLOT, jobs), (META_SLOT, meta), (WATCH_SLOT, watch)):
        if slot not in html:
            raise ValueError(f"template slot missing: {slot}")
        html = html.replace(slot, _json(value))
    return html
