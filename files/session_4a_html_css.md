# Session 4A: Frontend HTML Structure & Dark Theme CSS

## Context
You are working on Milestone 4 of the FiDi Transit Dashboard project. The Flask API server is running and serving data. This session builds the visual dashboard - HTML structure and CSS styling only (no JavaScript yet).

## Files You Need Access To
- `~/Projects/dashboard/frontend/index.html` (create - main deliverable)
- `~/Projects/dashboard/frontend/style.css` (create - main deliverable)
- `~/Projects/dashboard/backend/app.py` (modify - add route to serve frontend)

## Background
The dashboard must be:
- **Readable from 8-10 feet away** - Large fonts, high contrast
- **Portrait orientation** - Monitor rotated 90° (like an airport departure board)
- **Dark theme** - Low eye strain, looks professional, runs 24/7
- **Zero interaction** - No buttons, no forms, just information
- **MTA brand accurate** - Train line colors match official subway colors

Target resolution: 1920x1080 rotated to 1080x1920 (portrait)

---

## Your Task

### 1. Update `backend/app.py` - Serve Frontend Files

Add a route to serve the frontend:
```python
@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../frontend', path)
```

Don't forget to import: `from flask import send_from_directory`

---

### 2. Create `frontend/index.html` - Page Structure

Use the wireframe from DASHBOARD_PLAN.md as your guide:

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
└──────────────────────────────────┘
```

**HTML Structure:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FiDi Transit Dashboard</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <!-- Header with staleness indicator -->
    <header>
        <h1>FiDi Dash</h1>
        <div class="staleness-indicator">
            <span class="staleness-dot healthy"></span>
            <span class="staleness-text">Updated 10s ago</span>
        </div>
    </header>

    <!-- Subway section -->
    <section class="subway-section">
        <h2>🚇 SUBWAY</h2>
        
        <!-- Station: Wall St (4/5) -->
        <div class="station-group">
            <div class="station-header">
                <div class="line-badges">
                    <span class="line-badge line-4">4</span>
                    <span class="line-badge line-5">5</span>
                </div>
                <span class="station-name">Wall St</span>
            </div>
            <div class="arrivals">
                <div class="arrival">
                    <span class="line-indicator line-4">4</span>
                    <span class="time">2 min</span>
                </div>
                <div class="arrival">
                    <span class="line-indicator line-5">5</span>
                    <span class="time">6 min</span>
                </div>
            </div>
        </div>

        <!-- Repeat for other stations... -->
        <!-- Use placeholder data for now -->
        
    </section>

    <!-- Citibike section -->
    <section class="citibike-section">
        <h2>🚲 CITIBIKE</h2>
        
        <div class="citibike-station">
            <h3 class="dock-name">Broadway & Exchange Pl</h3>
            <div class="dock-status">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 73%"></div>
                </div>
                <div class="dock-counts">
                    <span class="bike-count">8 bikes</span>
                    <span class="dock-count">4 docks</span>
                </div>
            </div>
        </div>

        <!-- Second station... -->
        
    </section>

    <!-- Footer (future: service alerts) -->
    <footer>
        <p>📍 15 Broad St, FiDi</p>
    </footer>

    <!-- JavaScript will be added in Session 4B -->
    <!-- <script src="app.js"></script> -->
</body>
</html>
```

---

### 3. Create `frontend/style.css` - Dark Theme Styling

**Design Requirements:**

#### Color Palette
- Background: `#0a0a0a` (near black)
- Surface: `#1a1a1a` (dark gray cards)
- Text primary: `#e0e0e0` (off-white)
- Text secondary: `#999999` (medium gray)
- Accent: `#4a9eff` (blue for links/highlights)

#### MTA Official Line Colors
```css
.line-1 { background: #ee352e; } /* Red */
.line-2 { background: #ee352e; }
.line-3 { background: #ee352e; }
.line-4 { background: #00933c; } /* Green */
.line-5 { background: #00933c; }
.line-6 { background: #00933c; }
.line-7 { background: #b933ad; } /* Purple */
.line-a { background: #0039a6; } /* Blue */
.line-c { background: #0039a6; }
.line-e { background: #0039a6; }
.line-b { background: #ff6319; } /* Orange */
.line-d { background: #ff6319; }
.line-f { background: #ff6319; }
.line-m { background: #ff6319; }
.line-g { background: #6cbe45; } /* Light green */
.line-j { background: #996633; } /* Brown */
.line-z { background: #996633; }
.line-l { background: #a7a9ac; } /* Gray */
.line-n { background: #fccc0a; } /* Yellow */
.line-q { background: #fccc0a; }
.line-r { background: #fccc0a; }
.line-w { background: #fccc0a; }
.line-s { background: #808183; } /* Dark gray */
```

#### Typography
```css
/* Base font sizes for 1080x1920 portrait display */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 18px;
}

h1 { font-size: 48px; }  /* Header */
h2 { font-size: 36px; }  /* Section titles */
h3 { font-size: 24px; }  /* Station names */

.time { font-size: 56px; }  /* Arrival times - LARGEST */
.station-name { font-size: 28px; }
.line-badge { font-size: 32px; }
```

#### Staleness Indicator
```css
.staleness-dot {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    display: inline-block;
}

.staleness-dot.healthy { background: #00ff00; }  /* Green */
.staleness-dot.warning { background: #ffaa00; }  /* Yellow */
.staleness-dot.critical { background: #ff0000; } /* Red */
```

#### Citibike Progress Bars
```css
.progress-bar {
    width: 100%;
    height: 30px;
    background: #333;
    border-radius: 8px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #00ff88, #00cc66);
    transition: width 0.5s ease;
}

/* Red when critically full/empty */
.progress-fill.critical {
    background: linear-gradient(90deg, #ff4444, #cc0000);
}
```

#### Layout
```css
body {
    background: #0a0a0a;
    color: #e0e0e0;
    margin: 0;
    padding: 20px;
    max-width: 1080px;  /* Portrait width */
    margin: 0 auto;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 0;
    border-bottom: 2px solid #333;
}

section {
    margin: 40px 0;
    padding: 20px;
    background: #1a1a1a;
    border-radius: 12px;
}

.station-group {
    margin: 30px 0;
    padding: 20px;
    background: #252525;
    border-radius: 8px;
}

.arrivals {
    display: flex;
    flex-direction: column;
    gap: 15px;
    margin-top: 15px;
}

.arrival {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.line-badge {
    display: inline-block;
    width: 48px;
    height: 48px;
    line-height: 48px;
    text-align: center;
    border-radius: 50%;
    color: white;
    font-weight: bold;
}
```

---

## Requirements

### Accessibility
- High contrast ratios (WCAG AA minimum)
- Semantic HTML (proper heading hierarchy)
- No color-only information (use icons + text)

### Responsiveness
- Fixed layout for 1080x1920 (portrait monitor)
- Don't use media queries - this is single-purpose hardware
- Test at actual resolution before deploying to Pi

### Performance
- Minimal CSS (< 10KB)
- No external fonts (system fonts only)
- No animations (yet) - add in optimization phase if needed

---

## Acceptance Criteria
- [ ] HTML structure matches wireframe layout
- [ ] Dark theme applied consistently
- [ ] MTA line colors accurate (compare to official subway map)
- [ ] Text readable from 8 feet away (test physically)
- [ ] Staleness indicator visible and styled (green/yellow/red states)
- [ ] Citibike progress bars render correctly
- [ ] No JavaScript errors in console (since no JS yet)
- [ ] Page loads at `http://localhost:5000` when Flask is running

---

## Testing Checklist

### 1. Visual inspection
```bash
cd ~/Projects/dashboard
source venv/bin/activate
python backend/app.py

# Open in browser:
# http://localhost:5000

# Check:
# - Dark background renders
# - All sections visible
# - Colors match MTA branding
# - Layout matches wireframe
```

### 2. Distance readability test
```bash
# Open dashboard on monitor
# Stand 8-10 feet away
# Can you read the largest arrival times?
# Can you distinguish line colors?
```

### 3. Color contrast check
Use browser dev tools or https://webaim.org/resources/contrastchecker/
- White text on black: ✓ (AAA)
- Line badges on dark bg: ✓ (Check each line color)

### 4. Different data states
Manually edit HTML to test:
- No trains (empty arrivals)
- All docks full (100% progress bar)
- Stale data (red staleness dot)

---

## Example CSS Structure
```
style.css
├── Reset & Base Styles
├── Color Variables (MTA lines)
├── Typography Scale
├── Layout (header, sections, footer)
├── Components
│   ├── Staleness indicator
│   ├── Station groups
│   ├── Line badges
│   ├── Arrival times
│   ├── Citibike progress bars
│   └── Dock counts
└── Utility Classes
```

---

## Deliverables
After this session, you should have:
1. `frontend/index.html` with complete structure and placeholder data
2. `frontend/style.css` with full dark theme styling
3. Updated `backend/app.py` to serve the frontend
4. A beautiful static dashboard at `http://localhost:5000`

**No dynamic data yet** - that's Session 4B's job (JavaScript).

---

## Next Session
Session 4B will add JavaScript to fetch real data from the API and update the DOM dynamically.

---

## Reference Links
- MTA line colors: https://new.mta.info/map/5256
- CSS Grid layout: https://css-tricks.com/snippets/css/complete-guide-grid/
- Dark mode best practices: https://web.dev/prefers-color-scheme/
- WCAG contrast checker: https://webaim.org/resources/contrastchecker/
