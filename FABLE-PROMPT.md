# Prompt for Claude Fable — auto-updating internship board

Everything between the rules below is the prompt. Paste it as-is. Notes for *you*
(not for Fable) are collected at the bottom of this file.

---

Build me a static website that lists currently-open internships in electrical
engineering, firmware/embedded, robotics, computer architecture and FPGA/silicon
design — restricted to positions **outside the United States** — and that refreshes
itself once a day without me touching it. It will be hosted on GitHub Pages, so the
site itself must be fully static: no server, no database, no runtime API calls from
the browser.

## Architecture

Three stages, cleanly separated, each independently runnable and testable:

1. **Fetch** — one adapter per applicant-tracking system (ATS). Each adapter takes a
   source config and returns a list of raw postings. Adapters never filter.
2. **Normalize + filter** — map every raw posting into one flat schema, then apply the
   location, seniority and discipline filters. Pure functions, no network.
3. **Render** — read the filtered dataset plus the previous run's dataset, and emit a
   single self-contained `index.html`.

Write it in **Python 3.11+**. Dependencies: `requests` only, pinned in
`requirements.txt`. No frameworks, no static-site generators, no build toolchain, no
npm. The rendered page must have zero JavaScript dependencies except the Google Fonts
stylesheet — all filtering and sorting happens client-side in vanilla JS over a JSON
blob inlined in the page.

## Repository layout

```
.
├── .github/workflows/refresh.yml
├── sources.yml               # the source registry — the only file I edit routinely
├── scraper/
│   ├── __init__.py
│   ├── main.py               # orchestrates fetch → filter → render
│   ├── adapters/
│   │   ├── greenhouse.py
│   │   ├── lever.py
│   │   ├── ashby.py
│   │   ├── recruitee.py
│   │   └── workday.py
│   ├── filters.py
│   └── render.py
├── templates/base.html       # the design system — see "Visual design" below
├── data/
│   ├── jobs.json             # current filtered dataset, committed each run
│   └── history.json          # id → {first_seen, last_seen}, committed each run
├── index.html                # generated; GitHub Pages serves this
├── requirements.txt
└── tests/
```

## The normalized schema

Every posting, from every source, becomes exactly this:

```python
{
  "id":            str,   # stable: f"{source_slug}:{ats_job_id}"
  "company":       str,
  "title":         str,
  "location_raw":  str,   # verbatim from the ATS
  "country":       str,   # resolved: "Canada" | "China" | "Hong Kong" | "United Kingdom" | ...
  "city":          str,
  "url":           str,   # direct apply/posting link
  "posted_at":     str,   # ISO 8601, or null if the ATS doesn't expose it
  "first_seen":    str,   # ISO date, from history.json
  "last_seen":     str,   # ISO date, this run
  "track":         str,   # one of the discipline buckets below
  "source":        str,   # "greenhouse" | "lever" | ...
  "is_new":        bool,  # first_seen within the last 7 days
}
```

`id` must be stable across runs — it is what makes the "new posting" badge and the
first-seen tracking work. Never derive it from the title or from array position.

## Filters

Three gates, applied in order. Each gate lives in `filters.py` as a pure function with
its keyword lists as module-level constants, so I can tune them without reading code.

**1 — Location.** Keep only postings whose resolved country is not the United States.
Drop anything that resolves to a US state, "Remote - US", "United States", or a US
city. Ambiguous or unresolvable locations go to a `data/unresolved.json` file rather
than being silently dropped or silently kept — I want to see what the resolver
couldn't classify. Build the country resolver as an explicit lookup table over
city/region strings, not a regex guess.

Put the allowed-country list in `sources.yml` as a top-level key so I can widen it
later (right now: Canada, China, Hong Kong, Taiwan, Singapore, United Kingdom,
Germany, Netherlands, Ireland, Israel, Japan, South Korea, Australia).

**2 — Seniority.** Keep only internships and co-ops. Match on title against
`intern`, `internship`, `co-op`, `coop`, `student`, `new grad`, `graduate program`,
`placement`, `apprentice`, `实习`, `校招`. Explicitly exclude titles containing
`manager`, `director`, `senior`, `staff`, `principal`, `lead`, `II`, `III` unless the
word `intern` also appears.

**3 — Discipline.** Assign a track by keyword match against title and description.
Drop anything that matches none of them.

| track | matches on |
|---|---|
| `Silicon & FPGA` | fpga, rtl, asic, verilog, systemverilog, vhdl, soc, silicon, physical design, design verification, dv, uvm, tapeout, semiconductor, chip |
| `Computer Architecture` | computer architecture, microarchitecture, cpu, gpu, risc-v, cache, memory subsystem, performance modeling |
| `Embedded & Firmware` | firmware, embedded, rtos, freertos, bare metal, device driver, bsp, microcontroller, mcu, arm cortex, bootloader |
| `Hardware & PCB` | hardware engineer, pcb, schematic, altium, signal integrity, power electronics, analog, mixed-signal, board bring-up, hardware validation |
| `Robotics & Controls` | robotics, robot, motion control, control systems, mechatronics, ros, ros2, slam, perception, autonomy, actuator, motor control |

A posting matching several tracks takes the first match in the table order above.
Store the losing matches in a `also_matched` list so the UI can show them as secondary
tags.

## Source registry

`sources.yml` holds one entry per company. Shape:

```yaml
allowed_countries: [Canada, China, Hong Kong, ...]

sources:
  - slug: tenstorrent-university
    company: Tenstorrent
    ats: greenhouse
    board: tenstorrentuniversity
  - slug: waabi
    company: Waabi
    ats: lever
    board: waabi
```

### Adapters — endpoint patterns

I have **verified these four myself**; they return JSON, need no auth, no key, no
POST body:

| ATS | Endpoint | Verified against |
|---|---|---|
| Greenhouse | `GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true` | `tenstorrentuniversity` — 27 jobs, fields `id, title, location.name, absolute_url, updated_at, content` |
| Lever | `GET https://api.lever.co/v0/postings/{board}?mode=json` | `waabi` — array, fields `id, text, hostedUrl, applyUrl, createdAt, categories.{location, team, commitment}, descriptionPlain` |
| Ashby | `GET https://api.ashbyhq.com/posting-api/job-board/{board}` | `cohere` — `.jobs[]`, fields `id, title, location, secondaryLocations, jobUrl, applyUrl, publishedAt, descriptionPlain, department, team` |
| Recruitee | `GET https://{board}.recruitee.com/api/offers/` | `huaweicanada` — `.offers[]`, fields `id, title, slug, location, city, country, department, careers_url, published_at, description, requirements` |

Seed `sources.yml` with these, which I have confirmed resolve:

```yaml
- {slug: tenstorrent-university, company: Tenstorrent,   ats: greenhouse, board: tenstorrentuniversity}
- {slug: waabi,                  company: Waabi,         ats: lever,      board: waabi}
- {slug: kepler,                 company: Kepler Communications, ats: lever, board: kepler}
- {slug: cohere,                 company: Cohere,        ats: ashby,      board: cohere}
- {slug: huawei-canada,          company: Huawei Canada, ats: recruitee,  board: huaweicanada}
- {slug: samsung-ai-toronto,     company: Samsung AI Center Toronto, ats: greenhouse, board: saictoronto}
```

**Workday** is the fifth adapter and covers a lot of hardware employers (Altera,
Marvell, Micron, Analog Devices, Rockwell Automation). Its pattern is a POST:

```
POST https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
Content-Type: application/json
{"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
```

paginated by `offset` until `total` is exhausted. Each result carries `title`,
`externalPath`, `locationsText`, `postedOn`. The full posting URL is
`https://{tenant}.{dc}.myworkdayjobs.com/{site}{externalPath}`.

**I have not verified the individual Workday tenants**, so treat every `{tenant}`,
`{dc}` and `{site}` value as unconfirmed. For each Workday company, discover the real
values by loading the public board in a browser, watching the network tab for the
`/wday/cxs/.../jobs` request, and copying the path from it. Add the source to
`sources.yml` only once you have fetched a non-empty response. Do not guess and commit.

### Companies with no usable adapter

Google, Apple, NVIDIA, Microsoft, Amazon, Tesla, Qualcomm, AMD, Intel, Cisco, Ciena
and Synopsys all run bespoke or heavily-protected career platforms (Phenom, Eightfold,
in-house). Do **not** attempt to scrape rendered HTML, defeat bot protection, drive a
headless browser, or use an unofficial endpoint that requires spoofed headers.

Instead: `sources.yml` supports a second list, `watch:`, of `{company, url, note}`
entries that render at the bottom of the page as a short "check these manually" strip.
It is static, it costs nothing, and it means the big names don't silently vanish from
a board that is supposed to be about them.

If any of those companies later exposes a documented public JSON endpoint, adding it
should be a new adapter file plus a `sources.yml` line — nothing else.

## Robustness — this is the part that decides whether the site is trustworthy

- **Isolate every source.** One failing adapter must never abort the run or empty the
  board. Wrap each source in try/except, log the failure, and continue.
- **Never regress on failure.** If a source returns zero results this run but returned
  results last run, keep the previous run's rows for that source and mark them
  `stale: true`. Only drop a posting after it has been absent for **3 consecutive
  runs** — ATS APIs flake, and a listing blinking out for one night is not the same as
  a closed role.
- **Surface health in the UI.** The page header shows the last successful run time and,
  if any source failed, a small muted line naming which ones. I want to be able to tell
  at a glance whether I am looking at a fresh board or a half-broken one.
- **Rate-limit politely.** Sequential requests, 1-second delay between sources, a
  descriptive `User-Agent` with a contact URL, 15-second timeout, 2 retries with
  exponential backoff on 5xx only — never retry a 4xx.
- **Determinism.** Sort the dataset deterministically before writing `jobs.json`, so a
  run with no changes produces a byte-identical file and therefore no commit.

## Visual design

**The repo already contains `templates/base.html`, which is the finished design. Do
not redesign it, do not swap the fonts, do not "modernize" it.** Your job is to turn
its hardcoded `DATA` array into a template slot and wire the filter chips to the
generated tracks and countries. Everything else — the token blocks, the row layout,
the fit meter, the status pills, the sticky control bar — stays.

For reference, so you can tell when you've broken it, the system is:

- Type: **Archivo** (display, 500/600/700), **IBM Plex Sans** (body), **IBM Plex Mono**
  (labels, dates, tabular data). One Google Fonts `<link>`, nothing else external.
- Light tokens: ground `#F2F4F0`, surface `#FFFFFF`, surface-2 `#EAEEE9`, line
  `#D5DCD5`, line-soft `#E4E9E3`, ink `#131A17`, ink-2 `#455049`, ink-3 `#6E7B73`,
  accent `#0E6B4C`, accent-soft `#DCEBE3`, gold `#9A6C16`, gold-soft `#F3E7CC`, oxide
  `#A8391F`, oxide-soft `#F6DED6`, steel `#3D5F7A`, steel-soft `#DEE7EE`.
- Dark tokens: ground `#0E1412`, surface `#161D1A`, surface-2 `#1D2622`, line
  `#2B3833`, line-soft `#232E29`, ink `#E7EDE8`, ink-2 `#A9B7AF`, ink-3 `#7E8D85`,
  accent `#43BC8C`, accent-soft `#123529`, gold `#D9A343`, gold-soft `#3A2E14`, oxide
  `#E0785C`, oxide-soft `#3B211A`, steel `#82AECE`, steel-soft `#1B2A34`.
- Theme handling is already correct in the file — a bare `:root` light palette, a
  `@media (prefers-color-scheme: dark)` block guarded as `:root:not([data-theme="light"])`,
  and a `:root[data-theme="dark"]` block. Preserve all three. Do not move a color's
  only definition inside a media query.
- Radius 5px. Rows are `<details>` with a 3px left stripe coloured by state. Numbers
  use `font-variant-numeric: tabular-nums`.

Changes the new data model *does* require:

- The fit meter has no meaning for scraped rows — replace that column with **age**
  ("new" pill if `is_new`, otherwise "seen 12d"), using the same visual weight.
- Filter chips become: country, track, company, and a "new this week" toggle.
- The status pill now encodes freshness: `new` (accent), `open` (steel), `stale` (gold).
- Add a result count and a "last refreshed" timestamp in the header.

## The daily refresh

`.github/workflows/refresh.yml`:

- Trigger: `schedule` with `cron: "0 5 * * *"` — 05:00 UTC, which is midnight in
  America/Toronto during EDT and 1am during EST. Also `workflow_dispatch` so I can run
  it by hand.
- `permissions: contents: write`.
- Steps: checkout, setup-python 3.11, pip install, run `python -m scraper.main`, then
  commit `index.html data/` **only if the diff is non-empty**, with message
  `chore: refresh listings (N open, M new)`.
- Configure Pages to deploy from the `main` branch root. Do not use
  `actions/deploy-pages` — committing the generated `index.html` and letting Pages
  serve the branch is one fewer moving part, and the commit is already happening.
- Add a concurrency group so overlapping manual runs can't race the commit.

## Local development

`python -m scraper.main --dry-run` fetches and filters but writes nothing, printing a
summary table to stdout. `--only tenstorrent-university` restricts to one source.
`--offline` renders from the committed `data/jobs.json` without any network calls, so I
can iterate on the template in a second.

## Tests

`pytest`, no network. Fixture JSON captured from each of the four verified endpoints,
committed under `tests/fixtures/`. Cover: each adapter's normalization; the country
resolver against a table of tricky strings (`"Toronto, ON, Canada"`, `"Remote - US"`,
`"Shanghai, China"`, `"Hong Kong SAR"`, `"Austin, Texas, United States"`, `"Waterloo,
Ontario, Canada"`); the seniority filter against titles that should and shouldn't
match; and the "3 consecutive misses before removal" logic, which is the easiest thing
here to get subtly wrong.

## Acceptance criteria

I will consider this done when:

1. `python -m scraper.main` runs clean from a fresh clone and writes a valid
   `index.html`, `data/jobs.json` and `data/history.json`.
2. Opening `index.html` directly from the filesystem shows a working board — filters,
   sort, and expand-a-row all function with no console errors.
3. Zero US-located postings appear, and `data/unresolved.json` is either empty or
   contains only genuinely ambiguous strings.
4. Killing the network mid-run (or pointing one source at a bad board token) produces
   a complete page with that source marked failed, not a crash and not an empty board.
5. `pytest` passes.
6. The page is visually indistinguishable from `templates/base.html` apart from the
   documented column changes.
7. A second consecutive run with no upstream changes produces no git diff.

## Explicitly out of scope

No editorial or hand-written commentary — this is a pure listings board. No LLM or
paid API calls anywhere in the pipeline. No secrets, tokens or keys of any kind; if a
source needs auth, it does not belong here. No headless browsers or bot-protection
workarounds. No email or push notifications. No user accounts, no saved state beyond
`localStorage` for the viewer's own filter preferences.

## Before you write code

Read `templates/base.html` first and tell me, in a short paragraph each: how you plan
to slot generated data into it, how you'll structure the country resolver, and what
you think the most likely cause of a silently-wrong board is. Then build it.

---

## Notes for you, not for Fable

**Two things that will bite you later, neither of which belongs in the prompt:**

1. **GitHub disables scheduled workflows after 60 days of repository inactivity**, and
   commits made by `GITHUB_TOKEN` do not reliably count as activity. So a board that
   runs perfectly can go quiet after two months of you not touching the repo, with no
   error anywhere. Either push a trivial commit every few weeks, or add a second
   workflow that re-enables the schedule, or just diarize a check. Watch for this
   around early November.

2. **Actions cron is best-effort, not punctual.** Scheduled runs are routinely delayed
   5–30 minutes at peak times and are occasionally skipped entirely under load. "Every
   day at midnight" will in practice mean "most nights, some time after midnight." That
   is fine for a job board; it would not be fine for anything you were relying on to be
   exact.

**On the source registry.** The four verified adapters cover six companies, which is a
thin board on day one. The realistic growth path is Workday — Altera, Marvell, Micron,
ADI and Rockwell between them are a large share of the hardware co-op supply in Canada,
and they all speak the same POST protocol. Doing that discovery once buys you more
coverage than any other hour you could spend on this.

**On the big names.** Google, Apple, NVIDIA and Qualcomm are the companies you actually
care about and they are exactly the ones you can't scrape cleanly. The `watch:` strip is
a deliberate concession — it keeps them visible without pretending to automation you
don't have. If it starts feeling like dead weight, the honest alternative is an RSS or
email alert from each of their career sites, not a scraper.

**One scope question worth settling before you start.** The current filter is
"anywhere but the US," which is broader than the Canada/China board you have now — it
will pull in London, Munich, Tel Aviv, Tokyo. That is probably what you want for a
public site, and it makes the board considerably less empty. But if you'd rather it
stay Canada/China-focused, cut `allowed_countries` down before the first run rather
than after, so you don't spend a week tuning filters against postings you'll never
apply to.
