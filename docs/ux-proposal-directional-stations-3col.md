# UX Proposal: Station Grouping w/ 3-Column Direction Layout (Uptown | Station | Downtown)

Date: 2026-02-07

## Goals
- Reduce confusion by **separating direction** (Uptown vs Downtown) and placing **minutes on the outer edges**.
- Keep each **station as a single grouped block**.
- Provide a **strong visual divider** between directions.
- Improve Citi Bike list usefulness by adding **walk time from 15 Broad St**, ordering **closest → farthest**, and **freezing that order** until manually changed.

---

## High-level layout
Each station renders as a **3-column grid**:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Uptown                 |  4 5 Wall St                         |   Downtown  │
├─────────────────────────┼───────────────────────────────────────┼────────────┤
│  4m | 2 Wakefield        ||  3 New Lots              | 5m       │
│  7m | 5 E 180 St         ||  4 Brooklyn Br           | 8m       │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key idea
- **Minutes** live on the **outside edges**: left for Uptown, right for Downtown.
- **Destination text** is closer to the center, adjacent to the thick divider.

---

## Station block diagram (more explicit)

(Per your feedback: no separate “UPTOWN | STATION | DOWNTOWN” header row — it’s merged into the station title row.)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Uptown                 |  4 5 Wall St                         |   Downtown  │
├─────────────────────────┼───────────────────────────────────────┼────────────┤
│  [ETA] | [Train + Dest]  ||  [Train + Dest]          | [ETA]    │
├─────────────────────────┼───────────────────────────────────────┼────────────┤
│  4m   | 2 Wakefield       ||  3 New Lots              | 5m       │
│  7m   | 5 E 180 St        ||  4 Brooklyn Br           | 8m       │
│       |                   ||                          |          │
└─────────────────────────┴───────────────────────────────────────┴────────────┘
```

### Row-capping / alignment
- Cap to **2 rows per direction**.
- If one side has fewer, leave **blanks** to preserve alignment.

### Visual divider
A thick divider `||` is shown above.
Implementation idea:
- Make the center separator a **double rule** or a **thick vertical bar**.
- Optionally tint the background on each side (very subtle):
  - Uptown side: cool tint
  - Downtown side: warm tint

---

## Behavior / edge cases (for feedback)

### 1) Uneven number of arrivals
- **Row-align** and leave blanks on the sparse side.
- Cap to **2 rows** per direction for now.

### 2) Destination shortening
Use a **curated abbreviation list** (kiosk-friendly). Examples:
- “Brooklyn Bridge–City Hall” → “Bklyn Br–City Hall”
- “East 180 St” → “E 180 St”

(We can still allow 2-line wrap as a fallback, but the primary strategy is abbreviations.)

### 3) Station header content
Station header can show:
- Line pills (e.g., `4` `5`) + station name (“Wall St”)
- Optional secondary info: “Downtown only: N via Rector” etc.

---

## Bug fix requested
**Issue:** “Wall 23” station shows “Wall” + “23” as two red circles, but “4/5 Wall” only shows “4”.

**Expected:** each station shows **all line options** (e.g., `4` and `5`), consistently.

Acceptance criteria:
- The station header for each configured stop renders **all routes served** at that stop (or at least all routes we’re tracking there).

---

## Citi Bike improvement requested

### Add walk time from: **15 Broad Street**
Make walk time part of the **station header**, e.g.:

```
Broadway & Morris — 5 min (0.3 mi) away
[status bar]  [⚡ e-bikes]  [docks]
```

### Ordering rules
- Sort stations by **walk time (or distance)** ascending.
- **Freeze order** until you explicitly ask to re-order.
  - Interpretation: once computed and displayed, we keep a stable ordering even if availability changes.

Implementation notes (for discussion):
- Use a single “home coordinate” (geocode 15 Broad St once; store lat/lon in config).
- For walk time:
  - v1: simple distance → time estimate (e.g., 1.4 m/s) for offline reliability.
  - v2: real walking routes via a routing API (more accurate, but adds dependency + key).

---

## Locked-in decisions (from your feedback)
1) Station header: **route pills + station name** (e.g., `4 5 Wall St`).
2) Arrivals rows: cap **both directions to 2 rows**, and **row-align with blanks**.
3) Citi Bike order freeze: **static** based on computed distance; do not reorder unless you ask.

---

## Next step
Once you approve this layout, I’ll:
1) Create a small HTML/CSS prototype for one station block.
2) Update the renderer to map arrivals into (uptown[], downtown[]).
3) Implement the Citi Bike walk-time line and stable ordering.
