# Offshore Bench

A self-refreshing static board of currently-open internships and co-ops in
electrical engineering, silicon/FPGA, embedded, computer architecture and
robotics — restricted to positions outside the United States.

A GitHub Actions workflow runs the scraper once a day, commits the regenerated
`index.html` + `data/` when anything changed, and GitHub Pages serves the
branch. No server, no database, no JavaScript dependencies beyond one Google
Fonts stylesheet.

## How it works

Three stages, each independently runnable:

1. **Fetch** — one adapter per ATS (`scraper/adapters/`): Greenhouse, Lever,
   Ashby, Recruitee, Workday. Adapters never filter.
2. **Normalize + filter** — every raw posting becomes one flat schema, then
   three gates apply in `scraper/filters.py`: location (country resolver —
   an explicit lookup table; ambiguous strings go to `data/unresolved.json`),
   seniority (internships/co-ops only), and discipline (track assignment by
   keyword).
3. **Render** — `scraper/render.py` fills the three JSON slots in
   `templates/base.html` and writes `index.html`.

Postings that vanish for a single run are kept and marked **stale** — a
listing is only dropped after three consecutive absences, and a source that
fails outright freezes its rows rather than emptying the board. The page
header names any failed sources.

## Routine editing

`sources.yml` is the only file you touch routinely:

- `allowed_countries` — the country whitelist.
- `sources` — one line per company board. Greenhouse/Lever/Ashby/Recruitee
  need a `board` token; Workday needs `tenant`/`dc`/`site`, which you get by
  loading the public board in a browser and copying the path from the
  `/wday/cxs/.../jobs` request in the network tab. Only add a Workday source
  after fetching a non-empty response yourself.
- `watch` — companies with no scrapeable endpoint, rendered as the
  "check these manually" strip.

Keep entries in flow style (`- {key: value, ...}`) and quote values that
contain commas — the file is parsed by `scraper/registry.py`, not PyYAML.

Filter keyword lists (seniority terms, track keywords, the country tables)
are module-level constants at the top of `scraper/filters.py`.

## Local development

```
pip install -r requirements.txt
python -m scraper.main                   # full run: writes index.html + data/
python -m scraper.main --dry-run         # fetch + filter, write nothing
python -m scraper.main --only waabi      # restrict fetching to one source
python -m scraper.main --offline         # re-render from committed data, no network
pytest                                   # no network; fixtures under tests/fixtures/
```

Open `index.html` straight from the filesystem — everything is inline.

## Housekeeping

- GitHub disables scheduled workflows after 60 days of repository inactivity,
  and `GITHUB_TOKEN` commits don't reliably count. If the board goes quiet,
  check Actions → the `refresh` workflow for a disabled schedule.
- Actions cron is best-effort: the 05:00 UTC run routinely lands 5–30 minutes
  late and is occasionally skipped under load. Fine for a job board.
