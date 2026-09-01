# Offshore Bench

Summer 2027 EE / silicon / robotics internships outside the US — 42 entries across
Canada, mainland China and Hong Kong, filterable by region, track and status.

Open `index.html` in a browser. No build step, no dependencies, no server —
everything is inline except the Google Fonts stylesheet.

## Editing

All the listings live in one place: the `DATA` array in the `<script>` block near the
bottom of `index.html`. One object per opportunity:

```js
{
  co:     "Tenstorrent",                       // company
  role:   "RTL Design Intern · CPU/AI Hardware",
  org:    "Startup",                           // Big tech | Startup | Research lab | Program
  region: "Canada",                            // Canada | China | Hong Kong
  city:   "Toronto, ON",
  track:  "Silicon & FPGA",                    // must match a string in TRACKS
  fit:    5,                                   // 1–5, drives the fit meter
  status: "watch",                             // closing | open | soon | watch | blocked
  when:   "Rolling · check monthly",           // short window/deadline text
  sort:   2,                                   // lower = more urgent, drives default sort
  flag:   "eligibility",                       // optional badge on the row
  url:    "https://tenstorrent.com/en/university",
  notes:  ["Plain note.", "flag|Note rendered as a warning."],
  pay:    "—",
  term:   "4 months"
}
```

Two conventions worth knowing:

- A note prefixed `flag|` renders in the warning style — use it for eligibility traps,
  term-length mismatches and company-risk caveats, not for ordinary detail.
- `status` picks the row's colour stripe and badge. `sort` is what the default
  "By urgency" ordering actually reads, so nudge it rather than reordering the array.

Adding a new track means adding the string to both the `TRACKS` array and the entry's
`track` field, or the filter chip won't match anything.

## Status meanings

| status    | means                                                        |
|-----------|--------------------------------------------------------------|
| `closing` | live now with a deadline inside about a month                 |
| `open`    | live now, or cycle currently open                             |
| `soon`    | not open yet, expected window is known                        |
| `watch`   | rolling, unverified, or needs a direct email to confirm       |
| `blocked` | structurally ineligible — kept on the list to record why      |

## Housekeeping

Compiled 1 September 2026. Most Summer 2027 windows open November 2026 – February 2027,
so dates shown for unopened windows are last cycle's, used as a forecast. Re-verify
before relying on any of them.
