# 🚇 FiDi Transit Dashboard — Project Plan

**Codename:** FiDi Dash
**Owner:** You + Claude (co-founder)
**Location:** 15 Broad St, Financial District, NYC
**Hardware:** Raspberry Pi + spare monitor
**Development Machine:** Mac Mini
**Target:** Working v1 prototype by end of February 2026
**Created:** February 6, 2026

---

## 1. Vision

A zero-touch, always-on wall-mounted display that answers one question every morning:
**"What's the fastest way out of FiDi right now?"**

Glance from across the room. No tapping, no scrolling, no phone required.

---

## 2. Scope

### v1 — Ship by Feb 28, 2026

| Data Source | Details | Priority |
|---|---|---|
| **MTA Subway** | Real-time arrivals at 6 stations/lines | 🔴 Critical |
| **Citibike** | Dock levels at 2 stations (expandable) | 🔴 Critical |
| **System Health** | Staleness indicator, auto-recovery | 🟡 Important |

### v2 — March / stretch

| Data Source | Details | Priority |
|---|---|---|
| **Uber/Lyft** | Pickup ETA at 1 Wall St / 40 Exchange Pl | 🟢 Nice to have |
| **Weather overlay** | Affects transit decisions | 🟢 Nice to have |
| **MTA Service alerts** | Planned work, delays | 🟡 Important |
| **Configurability** | Brother's setup, different stations | 🟡 Important |

---

## 3. Data Source Deep Dive

### 3a. MTA Subway — Real-Time GTFS-RT Feeds

The MTA publishes free, open GTFS-Realtime feeds. No API key required (as of 2025).
Feeds are protobuf-encoded and update every 30 seconds.

**Your stations and their feed groupings:**

| Station | Lines | GTFS-RT Feed | Feed URL | Direction |
|---|---|---|---|---|
| Wall St (4/5) | 4, 5 | Numbered (1-7) | `https://api.mta.info/api/subway/gtfs/gtfs-1234567` | Northbound (to GCT) |
| Wall St (2/3) | 2, 3 | Numbered (1-7) | Same as above | Northbound |
| Broad St | J | JZ Feed | `https://api.mta.info/api/subway/gtfs/gtfs-jz` | Westbound (toward Manhattan) |
| Rector St | 1 | Numbered (1-7) | Same as 4/5 feed | Northbound |
| Rector St | R, W | NQRW Feed | `https://api.mta.info/api/subway/gtfs/gtfs-nqrw` | Northbound |
| Fulton St | A, C | ACE Feed | `https://api.mta.info/api/subway/gtfs/gtfs-ace` | Uptown |

**Total feeds to poll: 4** (1234567, JZ, NQRW, ACE)
**Poll interval:** Every 30 seconds (matching MTA update frequency)

**Stop IDs:** Will need to be resolved from MTA's static GTFS `stops.txt`. Each platform has a directional suffix (N/S). We need the northbound/uptown platform IDs for each station.

**Recommended library:** `nyct-gtfs` (Python) — provides human-friendly parsing of the MTA's protobuf feeds with zero boilerplate.

### 3b. Citibike — GBFS Public Feeds

Completely open, unauthenticated JSON endpoints. Trivially easy.

| Endpoint | URL | Updates |
|---|---|---|
| Station Info (static) | `https://gbfs.citibikenyc.com/gbfs/en/station_information.json` | Rarely changes |
| Station Status (live) | `https://gbfs.citibikenyc.com/gbfs/en/station_status.json` | Every ~60 sec |

**Your target docks:**

| Dock | Approx. Location | Station ID |
|---|---|---|
| Broadway & Exchange Place | ~1 block south | TBD (resolve from station_information.json by lat/lng) |
| (Second dock TBD) | Nearest to 15 Broad | TBD |

**Data available per station:** `num_bikes_available`, `num_ebikes_available`, `num_docks_available`, `is_renting`, `is_returning`, `last_reported`

**Poll interval:** Every 60 seconds (sufficient for dock level changes)

### 3c. Uber/Lyft — DEFERRED TO v2

**Status:** Both Uber and Lyft have restricted their public APIs significantly.
- Uber's ride estimate endpoint requires privileged OAuth scopes and is deprecated in v1
- Lyft requires a business relationship / Lyft Business contact for API documentation access

**v2 plan:**
1. Register Uber developer account (free, immediate)
2. Attempt client_credentials OAuth flow for personal use (5 registered developers allowed)
3. If that fails, explore deep-link buttons as fallback (tap to open Uber/Lyft app with pre-filled pickup location)
4. Pickup addresses: 1 Wall St or 40 Exchange Pl (pedestrianized zone workaround)

**Risk level:** Medium-high. May not be possible without a business partnership.

---

## 4. Architecture

```
┌─────────────────────────────────────────────────┐
│                  RASPBERRY PI                    │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │           Python Backend Service          │   │
│  │                                           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────┐  │   │
│  │  │  MTA    │ │Citibike │ │  Health    │  │   │
│  │  │ Fetcher │ │ Fetcher │ │  Monitor  │  │   │
│  │  │ (30s)   │ │ (60s)   │ │           │  │   │
│  │  └────┬────┘ └────┬────┘ └─────┬─────┘  │   │
│  │       │           │             │         │   │
│  │       ▼           ▼             ▼         │   │
│  │  ┌──────────────────────────────────────┐│   │
│  │  │        Local HTTP API (Flask)        ││   │
│  │  │        localhost:5000/api/...        ││   │
│  │  └──────────────────┬───────────────────┘│   │
│  └─────────────────────┼────────────────────┘   │
│                        │                         │
│  ┌─────────────────────▼────────────────────┐   │
│  │         Frontend (HTML/CSS/JS)            │   │
│  │         Served by same Flask app          │   │
│  │         Auto-refreshes via fetch()        │   │
│  │         Fullscreen Chromium kiosk mode    │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         Chromium (kiosk mode)             │   │
│  │         --kiosk http://localhost:5000     │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
└─────────────────────────────────────────────────┘
         │
         ▼
    ┌──────────┐
    │ MONITOR  │  (HDMI from Pi)
    │ Portrait │  (recommended: rotate 90°)
    │ or       │
    │Landscape │
    └──────────┘
```

### Why this architecture?

- **Single machine, single process.** No Docker, no microservices, no database. This is a personal dashboard, not a distributed system.
- **Python backend.** Best MTA library ecosystem (`nyct-gtfs`), simple HTTP requests for Citibike, runs natively on Pi.
- **Flask as local web server.** Lightweight, battle-tested, serves both API and frontend.
- **Vanilla HTML/CSS/JS frontend.** No React, no build step, no npm. The Pi doesn't need to compile anything. The frontend just fetches JSON and renders it.
- **Chromium kiosk mode.** Full-screen browser, no address bar, no controls. Looks like a native app.
- **systemd service.** Auto-starts on boot, auto-restarts on crash.

### What we are NOT doing (and why):

| Temptation | Why we're skipping it |
|---|---|
| React / Next.js | Build tooling overhead, Pi doesn't need it |
| Docker | One app on one machine. Docker adds complexity for zero benefit here |
| Database | We only care about *right now*. No historical storage needed for v1 |
| WebSockets | Polling every 30s via fetch() is simpler and sufficient |
| Cloud hosting | The whole point is a local display. No cloud. No latency. No bills |
| Multiple services | One Python process. One. |

---

## 5. Information Hierarchy (UX)

The display must be readable from 8-10 feet away. Think airport departure board, not phone app.

### Layout Concept (portrait orientation — monitor rotated 90°):

Portrait is the better choice. Train arrivals are a naturally vertical list
(think Penn Station departure boards), and you get more rows without cramming.

```
┌──────────────────────────────────┐
│  FiDi Dash          ● Updated 10s│
├──────────────────────────────────┤
│                                  │
│  🚇 SUBWAY                       │
│                                  │
│  ④⑤ Wall St          2 min      │
│  to Grand Central     6 min      │
│                                  │
│  ②③ Wall St          5 min      │
│                       9 min      │
│                                  │
│  Ⓙ  Broad St         3 min      │
│                                  │
│  ①  Rector            4 min      │
│                       8 min      │
│                                  │
│  ⓇⓌ Rector           7 min      │
│                      14 min      │
│                                  │
│  ⒶⒸ Fulton           3 min      │
│                       5 min      │
│                                  │
├──────────────────────────────────┤
│                                  │
│  🚲 CITIBIKE                     │
│                                  │
│  Broadway & Exchange             │
│  ██████████░░  8 bikes   4 docks │
│                                  │
│  (Second Station)                │
│  ████░░░░░░░░  3 bikes  12 docks │
│                                  │
├──────────────────────────────────┤
│  ⚠ Service Alerts (v2)          │
│  📍 15 Broad St, FiDi            │
└──────────────────────────────────┘
```

### Design Principles:

1. **Largest text = next train arrival.** "2 min" should be readable from across the room.
2. **Color coding for urgency.** Green = plenty of time. Yellow = hurry. Red = you missed it / about to miss it.
3. **Staleness is visible.** The "Updated Xs ago" badge turns yellow at 60s, red at 120s.
4. **Dark theme default.** This display runs 24/7. Dark theme saves power and doesn't light up your apartment like a lighthouse at 3am.
5. **No interaction required.** Zero buttons, zero clicks. It just runs.
6. **Train line colors match MTA branding.** 4/5 = green, 2/3 = red, J = brown, 1 = red, R/W = yellow, A/C = blue. New Yorkers read these colors instinctively.

---

## 6. Development Loop — Milestones

Following the prescribed loop: Ideate → Design → Plan → Execute → Test → Use → Optimize → Refactor → Track → Return

### Milestone 0: Foundation (Feb 6–8) — IDEATE + DESIGN + PLAN ✅

| Task | Status |
|---|---|
| Define vision and scope | ✅ Done (this conversation) |
| Research all API data sources | ✅ Done |
| Identify risk (Uber/Lyft) and mitigate (defer to v2) | ✅ Done |
| Architecture decision | ✅ Done |
| Create DASHBOARD_PLAN.md | ✅ Done (this file) |
| Decide tech stack | ✅ Done |

**Output:** This document.

---

### Milestone 1: MTA Subway Data — Backend (Feb 8–11) — EXECUTE

**Goal:** Python script that prints next 2 arriving trains for each of your 6 station/line combos.

| Task | Est. Hours |
|---|---|
| Set up Python project structure on Mac Mini | 0.5h |
| Install `nyct-gtfs` and dependencies | 0.5h |
| Resolve stop IDs for all 6 stations from static GTFS `stops.txt` | 1h |
| Write fetcher for each of the 4 GTFS-RT feeds | 2h |
| Parse arrival times, filter to your stations + directions only | 2h |
| Format output: line, station, direction, minutes until arrival | 1h |
| Handle edge cases: no trains, feed errors, stale data | 1h |

**Acceptance criteria:** Run the script, see accurate arrival times that match the MTA app.

---

### Milestone 2: Citibike Data — Backend (Feb 11–12) — EXECUTE

**Goal:** Python script that prints bike count, e-bike count, and dock availability for your 2 stations.

| Task | Est. Hours |
|---|---|
| Fetch station_information.json, find your 2 station IDs by name/location | 1h |
| Fetch station_status.json, extract bike/dock counts | 1h |
| Handle: station offline, no data, API down | 0.5h |
| Structure data to make adding more stations trivial (config list) | 0.5h |

**Acceptance criteria:** Run the script, see numbers that match the Citibike app.

---

### Milestone 3: Local API Server (Feb 12–14) — EXECUTE

**Goal:** Flask app serving JSON endpoints that the frontend will consume.

| Endpoint | Returns |
|---|---|
| `GET /api/subway` | All train arrivals, grouped by station |
| `GET /api/citibike` | All dock statuses |
| `GET /api/health` | Last fetch times, error counts, uptime |

| Task | Est. Hours |
|---|---|
| Set up Flask app structure | 0.5h |
| Background scheduler for MTA fetches (every 30s) | 1h |
| Background scheduler for Citibike fetches (every 60s) | 0.5h |
| JSON API endpoints | 1h |
| Error handling and logging | 1h |
| In-memory cache (no database) | 0.5h |

**Acceptance criteria:** `curl localhost:5000/api/subway` returns accurate JSON.

---

### Milestone 4: Frontend Dashboard (Feb 14–18) — EXECUTE

**Goal:** Single HTML page that displays all transit data, auto-refreshes, looks great on a monitor.

| Task | Est. Hours |
|---|---|
| HTML layout matching the information hierarchy wireframe | 2h |
| CSS: dark theme, large fonts, MTA line colors | 2h |
| JavaScript: fetch from API endpoints, update DOM | 2h |
| Staleness indicator (green/yellow/red) | 1h |
| Auto-refresh every 15 seconds (frontend polls backend) | 0.5h |
| Responsive: test at monitor resolution | 1h |
| Edge states: no data, API down, stale data | 1h |

**Acceptance criteria:** Open `localhost:5000` in a browser, see a beautiful dashboard with live data.

---

### Milestone 5: Test + Validate (Feb 18–20) — TEST

| Task | Est. Hours |
|---|---|
| Compare dashboard arrivals vs MTA app for 1 full commute morning | 1h |
| Compare Citibike counts vs Citibike app | 0.5h |
| Simulate network failure (disconnect WiFi) — verify graceful degradation | 0.5h |
| Simulate backend crash — verify staleness indicator turns red | 0.5h |
| Test overnight (does it survive 12 hours running?) | passive |
| Fix all bugs found | 2-4h |

**Acceptance criteria:** Dashboard survives 24 hours with accurate data and graceful failure handling.

---

### Milestone 6: Raspberry Pi Deployment (Feb 20–23) — EXECUTE

| Task | Est. Hours |
|---|---|
| Flash Raspberry Pi OS Lite (or Desktop if needed for Chromium) | 0.5h |
| Install Python, pip, dependencies on Pi | 1h |
| Transfer project to Pi (git clone or scp) | 0.5h |
| Configure Chromium kiosk mode (auto-launch fullscreen) | 1h |
| Create systemd service for Flask backend (auto-start, auto-restart) | 1h |
| Configure Pi to auto-login and launch kiosk on boot | 1h |
| HDMI config: correct resolution, portrait rotation (90°) | 1h |
| Test on actual monitor | 1h |
| Disable screen blanking / sleep | 0.5h |

**Acceptance criteria:** Unplug Pi, plug it back in, dashboard appears automatically within 60 seconds.

---

### Milestone 7: Use It For Real (Feb 23–26) — USE

**Goal:** Live with the dashboard for 3+ days as your actual commute tool.

| What to track | How |
|---|---|
| Did the arrival times match reality? | Mental note each morning |
| Was the display readable from across the room? | Adjust font sizes |
| Did it crash or go stale? | Check staleness indicator |
| What information did you wish you had? | Write it down for v2 |
| What information was useless? | Consider removing it |

**Output:** A list of real-world feedback items for optimization.

---

### Milestone 8: Optimize + Refactor (Feb 26–28) — OPTIMIZE + REFACTOR

| Task | Est. Hours |
|---|---|
| Apply feedback from real-world use | 2-4h |
| Performance: reduce CPU/memory on Pi if needed | 1h |
| Code cleanup: docstrings, config file for station IDs | 2h |
| Create README.md with setup instructions (for brother / future you) | 1h |
| Create `config.yaml` for station customization | 1h |

**Acceptance criteria:** Your brother could set this up from the README alone.

---

### Milestone 9: Track + Return (Feb 28) — TRACK + RETURN

| Task | Output |
|---|---|
| Update STATUS.md with what shipped | STATUS.md |
| Document what worked, what didn't | Lessons learned |
| Prioritize v2 backlog | v2 roadmap |
| Celebrate 🎉 | Beer |

---

## 7. Tech Stack (Final)

| Layer | Technology | Rationale |
|---|---|---|
| Language | Python 3.11+ | Best MTA library, runs on Pi, you're building solo |
| MTA Data | `nyct-gtfs` library | Parses GTFS-RT protobuf natively, human-friendly API |
| Citibike Data | `requests` (stdlib-adjacent) | Simple JSON GET, no library needed |
| Web Server | Flask | Lightweight, serves API + static frontend |
| Scheduler | `APScheduler` | Background polling without threads/cron complexity |
| Frontend | Vanilla HTML + CSS + JS | No build step, no npm, no framework. Deploy = copy files |
| Browser | Chromium (kiosk mode) | Pre-installed on Pi OS, full-screen, auto-launch |
| Process Mgmt | systemd | Auto-start on boot, auto-restart on crash, logging |
| Config | YAML file | Easy to edit station lists without touching code |
| Version Control | Git | Push from Mac Mini, pull on Pi |

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| MTA changes feed URLs | Low | High | Log errors loudly, check MTA developer page |
| Citibike changes API format | Low | Medium | GBFS is an industry standard, unlikely to break |
| Pi SD card corruption | Medium | High | Use quality SD card, minimize writes, consider USB boot |
| WiFi drops in apartment | Medium | Medium | Staleness indicator alerts you. Data resumes on reconnect |
| MTA feed returns stale data | Medium | Low | Compare feed timestamp vs wall clock, show warning |
| Monitor burns in from static content | Low | Medium | Subtle CSS animation or periodic layout shift |
| Uber/Lyft API access denied for v2 | High | Low | Already deferred. Deep-link fallback ready |
| Scope creep (weather, buses, PATH...) | High | Medium | This plan. Stick to it. Ship v1 first |
| You get bored after Milestone 4 | Medium | Fatal | The "Use It For Real" milestone exists for this reason |

---

## 9. Project Structure

```
fidi-dash/
├── README.md                  # Setup guide for Pi deployment
├── DASHBOARD_PLAN.md          # This file
├── STATUS.md                  # Updated each milestone
├── config.yaml                # Station IDs, dock IDs, poll intervals
├── requirements.txt           # Python dependencies
│
├── backend/
│   ├── app.py                 # Flask app + API routes
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── mta.py             # MTA GTFS-RT fetcher + parser
│   │   └── citibike.py        # Citibike GBFS fetcher
│   ├── cache.py               # In-memory data store
│   └── health.py              # Uptime, last-fetch tracking
│
├── frontend/
│   ├── index.html             # Single-page dashboard
│   ├── style.css              # Dark theme, MTA colors, large fonts
│   └── app.js                 # Fetch + render loop
│
├── deploy/
│   ├── fidi-dash.service      # systemd unit file
│   ├── kiosk.sh               # Chromium kiosk launcher
│   └── setup-pi.sh            # One-shot Pi setup script
│
└── docs/
    └── STOP_IDS.md            # Reference: your stations + GTFS stop IDs
```

---

## 10. Configuration Design

```yaml
# config.yaml
location:
  name: "15 Broad St, FiDi"
  lat: 40.7074
  lng: -74.0113

subway:
  poll_interval_seconds: 30
  stations:
    - name: "Wall St"
      lines: ["4", "5"]
      stop_id: "TBD"        # Northbound platform
      direction: "N"
      priority: primary       # Largest display
    - name: "Wall St"
      lines: ["2", "3"]
      stop_id: "TBD"
      direction: "N"
      priority: secondary
    - name: "Broad St"
      lines: ["J"]
      stop_id: "TBD"
      direction: "W"          # Only one direction
      priority: secondary
    - name: "Rector St"
      lines: ["1"]
      stop_id: "TBD"
      direction: "N"
      priority: secondary
    - name: "Rector St"
      lines: ["R", "W"]
      stop_id: "TBD"
      direction: "N"
      priority: secondary
    - name: "Fulton St"
      lines: ["A", "C"]
      stop_id: "TBD"
      direction: "N"          # Uptown
      priority: secondary

citibike:
  poll_interval_seconds: 60
  stations:
    - name: "Broadway & Exchange Pl"
      station_id: "TBD"       # Resolve from station_information.json
    # Easy to add more:
    # - name: "Broad St & Water St"
    #   station_id: "TBD"

rideshare:                     # v2
  enabled: false
  pickup_addresses:
    - "1 Wall St, New York, NY"
    - "40 Exchange Pl, New York, NY"

display:
  theme: dark
  orientation: portrait        # monitor rotated 90°
  refresh_interval_ms: 15000   # Frontend polls backend
  staleness_warning_sec: 60
  staleness_critical_sec: 120
```

---

## 11. Definition of Done — v1

All of the following must be true:

- [ ] Dashboard displays next 2 arriving trains for all 6 station/line combos
- [ ] Dashboard displays bike count and dock count for 2 Citibike stations
- [ ] Data auto-refreshes without any user interaction
- [ ] Staleness indicator shows when data is old
- [ ] Dark theme, readable from 8+ feet away
- [ ] MTA line colors match official branding
- [ ] Runs on Raspberry Pi, starts automatically on boot
- [ ] Survives 24 hours without crashing
- [ ] Recovers automatically after power loss or network drop
- [ ] Adding a new station requires only editing config.yaml
- [ ] README exists that someone else could follow to set up their own

---

## 12. What v2 Looks Like (Not Now, but Documented)

Prioritized backlog for after v1 ships:

1. **Uber/Lyft pickup ETA** — Investigate API access, fall back to deep links
2. **MTA service alerts** — "No 4/5 service this weekend" banner
3. **Weather strip** — Temperature + precipitation affects transit choice
4. **Portrait mode layout** — If vertical monitor looks better
5. **Brother's config** — His stations, his Citibike docks, same codebase
6. **Historical patterns** — "The 4 train is usually 2 min late at 8:15am"
7. **Mobile view** — Access the dashboard from your phone when away
8. **Enterprise mode** — Multi-tenant config, lobby display for buildings

---

## Appendix A: Useful Links

| Resource | URL |
|---|---|
| MTA Developer Resources | https://www.mta.info/developers |
| MTA GTFS-RT API | https://api.mta.info/ |
| nyct-gtfs Python library | https://github.com/Andrew-Dickinson/nyct-gtfs |
| Citibike Station Status | https://gbfs.citibikenyc.com/gbfs/en/station_status.json |
| Citibike Station Info | https://gbfs.citibikenyc.com/gbfs/en/station_information.json |
| GBFS Specification | https://github.com/MobilityData/gbfs |
| Uber Developer Portal | https://developer.uber.com/ |
| Lyft Developer Portal | https://developer.lyft.com/ |
| Raspberry Pi OS | https://www.raspberrypi.com/software/ |

---

## Appendix B: Development Loop Reference

| Phase | What Happens | Output |
|---|---|---|
| **Ideate** | Brainstorm, explore problem space | Ideas, possibilities |
| **Design** | Decide on approach, architecture | Design doc, wireframes |
| **Plan** | Break into milestones, estimate | PLAN.md with milestones |
| **Execute** | Build the thing | Working code |
| **Test** | Verify it works | Passing tests, bug fixes |
| **Use** | Actually use it yourself | Real-world feedback |
| **Optimize** | Performance, UX improvements | Faster/better version |
| **Refactor** | Clean up technical debt | Cleaner codebase |
| **Track** | Log what happened, metrics | STATUS.md updates |
| **Return** | Loop back with learnings | Next iteration |

**The rule:** Don't skip phases. Most projects fail because people jump from Ideate straight to Execute.

---

*This plan is a living document. Update it as reality diverges from the plan — because it will.*
