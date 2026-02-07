# FiDi Transit Dashboard - Session Prompts README

## Overview
This folder contains pre-written session prompts for building the FiDi Transit Dashboard using OpenClaw (or any coding assistant). Each session corresponds to a milestone from DASHBOARD_PLAN.md.

## Quick Start

### Pre-Session Setup (Do this first!)
Run these commands on your Mac Mini before starting Session 1A:

```bash
# 1. Create project structure
cd ~/Projects
mkdir -p dashboard/backend/fetchers
mkdir -p dashboard/frontend
mkdir -p dashboard/deploy
mkdir -p dashboard/docs
mkdir -p dashboard/data/mta-static

cd dashboard

# 2. Download MTA static data (needed for Session 1A)
cd data/mta-static
curl -O http://web.mta.info/developers/data/nyct/subway/google_transit.zip
unzip google_transit.zip
ls stops.txt  # Verify it exists
cd ../..

# 3. Create config.yaml template
cat > config.yaml << 'EOF'
location:
  name: "15 Broad St, FiDi"
  lat: 40.7074
  lng: -74.0113

subway:
  poll_interval_seconds: 30
  stations:
    - name: "Wall St"
      lines: ["4", "5"]
      stop_id: "TBD"
      direction: "N"
    - name: "Wall St"
      lines: ["2", "3"]
      stop_id: "TBD"
      direction: "N"
    - name: "Broad St"
      lines: ["J"]
      stop_id: "TBD"
      direction: "W"
    - name: "Rector St"
      lines: ["1"]
      stop_id: "TBD"
      direction: "N"
    - name: "Rector St"
      lines: ["R", "W"]
      stop_id: "TBD"
      direction: "N"
    - name: "Fulton St"
      lines: ["A", "C"]
      stop_id: "TBD"
      direction: "N"

citibike:
  poll_interval_seconds: 60
  stations:
    - name: "Broadway & Exchange Pl"
      station_id: "TBD"
    - name: "Second Station TBD"
      station_id: "TBD"

display:
  theme: dark
  orientation: portrait
  refresh_interval_ms: 15000
  staleness_warning_sec: 60
  staleness_critical_sec: 120
EOF

# 4. Initialize git
git init
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.DS_Store
data/mta-static/*.zip
venv/
EOF

git add .
git commit -m "Initial project structure"

# 5. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 6. Create requirements.txt
cat > requirements.txt << 'EOF'
flask==3.0.0
APScheduler==3.10.4
requests==2.31.0
nyct-gtfs==1.4.0
pyyaml==6.0.1
protobuf==4.25.1
EOF

pip install -r requirements.txt

echo "✅ Setup complete! Ready for Session 1A."
```

---

## Session Files

### Week 1: Backend Development (Feb 8-14)

**Session 1A** - `session_1a_mta_stop_ids.md`
- **What:** Resolve MTA stop IDs from stops.txt
- **Input:** MTA static GTFS data, config.yaml
- **Output:** Updated config.yaml with all stop_ids filled in
- **Estimated time:** 1 hour
- **Test:** Run the script, verify no "TBD" values remain

**Session 1B** - `session_1b_mta_fetcher.md`
- **What:** Build real-time MTA subway data fetcher
- **Input:** config.yaml (with stop_ids), nyct-gtfs library
- **Output:** backend/fetchers/mta.py
- **Estimated time:** 2 hours
- **Test:** Compare output to MTA app during your commute

**Session 2** - `session_2_citibike_fetcher.md`
- **What:** Build Citibike dock status fetcher
- **Input:** Citibike GBFS API, config.yaml
- **Output:** backend/fetchers/citibike.py, updated config.yaml
- **Estimated time:** 1.5 hours
- **Test:** Compare dock counts to Citibike app

**Session 3A** - `session_3a_flask_api.md`
- **What:** Integrate fetchers into Flask API with background scheduling
- **Input:** Both completed fetchers
- **Output:** backend/app.py, backend/cache.py, backend/health.py
- **Estimated time:** 2 hours
- **Test:** `curl localhost:5000/api/subway` returns live data

---

### Week 2: Frontend Development (Feb 15-21)

**Session 4A** - `session_4a_html_css.md`
- **What:** Build HTML structure and dark theme CSS
- **Input:** Wireframe from DASHBOARD_PLAN.md, MTA line colors
- **Output:** frontend/index.html, frontend/style.css
- **Estimated time:** 2 hours
- **Test:** View at `http://localhost:5000`, check readability from 8 feet

**Session 4B** - `session_4b_javascript.md`
- **What:** Add JavaScript to fetch and display live data
- **Input:** Completed HTML/CSS, API endpoints
- **Output:** frontend/app.js
- **Estimated time:** 2 hours
- **Test:** Dashboard auto-refreshes every 15 seconds with live data

---

### Week 3: Deployment (Feb 22-28)

**Session 5** - Manual Testing (No prompt file)
- **What:** Use the dashboard during your commute for 3+ days
- **Output:** List of bugs, UX issues, feedback
- **Your job:** Document what works, what doesn't

**Session 6A** - `session_6a_pi_deployment.md`
- **What:** Create Raspberry Pi deployment scripts
- **Input:** Working dashboard on Mac
- **Output:** systemd service, kiosk launcher, setup script
- **Estimated time:** 1.5 hours
- **Test:** Deploy to Pi, verify auto-start on boot

---

## How to Use Each Session Prompt

### Method 1: OpenClaw with Direct File Upload
```bash
# Start OpenClaw coding session
openclaw

# In the OpenClaw interface:
# 1. Upload the session prompt file (e.g., session_1a_mta_stop_ids.md)
# 2. Upload any required input files mentioned in the prompt
# 3. Say: "Follow the instructions in this session prompt"
# 4. The assistant will build the deliverable(s)
```

### Method 2: Copy-Paste to Any Coding Assistant
```bash
# 1. Open the session prompt in a text editor
# 2. Copy the entire contents
# 3. Paste into Claude, ChatGPT, Cursor, etc.
# 4. Add: "Also, here are the input files: [attach files]"
# 5. Start coding
```

### Method 3: Use as Implementation Reference
```bash
# If you prefer to code yourself:
# 1. Read the session prompt for requirements
# 2. Use the code examples as templates
# 3. Follow the acceptance criteria checklist
# 4. Run the tests to verify completion
```

---

## Session Workflow Pattern

Each session follows this structure:

1. **Context** - What milestone you're on, what's already done
2. **Files You Need** - Input files and what you'll create
3. **Background** - Technical details, API info, architecture
4. **Your Task** - Specific deliverables with code examples
5. **Requirements** - Error handling, performance, edge cases
6. **Acceptance Criteria** - Checklist of what "done" means
7. **Testing Checklist** - How to verify it works
8. **Next Session** - What comes after this

---

## Tips for Success

### Do This:
✅ Complete sessions in order (dependencies exist)
✅ Run the tests after each session before moving on
✅ Commit to git after each session: `git commit -m "Completed Session 1A"`
✅ If a session fails, fix the issue before proceeding
✅ Take breaks between sessions (avoid marathon coding)

### Avoid This:
❌ Skipping sessions or combining them (recipe for bugs)
❌ Modifying session prompts mid-stream (stick to the plan)
❌ Proceeding with broken code (fix it before moving forward)
❌ Skipping the testing checklist (you'll regret it on the Pi)

---

## Troubleshooting

### "I don't have stops.txt"
Run the pre-session setup commands above. You need to download MTA's static GTFS data.

### "My assistant says it can't access files"
Make sure you're uploading the files mentioned in "Files You Need Access To" section.

### "A session produced broken code"
- Check the acceptance criteria - did all items pass?
- Review the testing checklist - which test failed?
- Provide the error message to your assistant for debugging
- Don't proceed to the next session until fixed

### "I want to change the architecture"
Don't. The architecture decisions are in DASHBOARD_PLAN.md and are final for v1. Changes create cascading bugs.

### "Session X is taking way longer than estimated"
- Are you adding features not in the prompt? (scope creep)
- Did you skip a previous session? (missing dependencies)
- Is your assistant stuck in a loop? (restart with clearer context)

---

## After Completing All Sessions

You should have:
- ✅ Working Flask backend serving live MTA + Citibike data
- ✅ Beautiful dark-themed frontend that auto-refreshes
- ✅ Deployment scripts ready for Raspberry Pi
- ✅ A dashboard you've tested with real-world usage
- ✅ Documentation for deploying additional instances

Ship it to your Pi and enjoy never missing a train again! 🚇

---

## v2 Planning (After Feb 28)

Once v1 is complete and you've lived with it for a few weeks, revisit DASHBOARD_PLAN.md Section 12 (What v2 Looks Like) to prioritize:
- Uber/Lyft pickup ETAs
- MTA service alerts
- Weather integration
- Your brother's configuration
- Historical pattern analysis

For v2, you'll create a new set of session prompts following the same pattern.

---

## Questions?

If you get stuck:
1. Re-read the session prompt carefully
2. Check the DASHBOARD_PLAN.md for context
3. Review the acceptance criteria - what specifically failed?
4. Ask your coding assistant to explain the error
5. If totally stuck, take a break and come back fresh

Remember: The goal is a working dashboard, not perfect code. Ship v1, then optimize.
