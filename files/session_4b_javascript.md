# Session 4B: Frontend JavaScript - Dynamic Data Fetching

## Context
You are working on Milestone 4 of the FiDi Transit Dashboard project. The HTML/CSS frontend exists with placeholder data. This session adds JavaScript to fetch live data from the Flask API and update the DOM automatically.

## Files You Need Access To
- `~/Projects/dashboard/frontend/app.js` (create - main deliverable)
- `~/Projects/dashboard/frontend/index.html` (modify - add script tag, update to use data attributes)
- `~/Projects/dashboard/frontend/style.css` (minor updates if needed)

## Background
The frontend needs to:
1. **Fetch data** from 3 API endpoints every 15 seconds
2. **Update the DOM** without page reload
3. **Handle errors** gracefully (show stale data, not blank screen)
4. **Update staleness indicator** based on data freshness
5. **Highlight urgent states** (trains arriving now, full/empty docks)

No frameworks. Vanilla JavaScript only.

---

## Your Task

### 1. Update `frontend/index.html` - Add Data Attributes

Modify the HTML to use data attributes for JavaScript targeting:

```html
<!-- Header staleness indicator -->
<div class="staleness-indicator" data-staleness-target>
    <span class="staleness-dot" data-staleness-dot></span>
    <span class="staleness-text" data-staleness-text>Updating...</span>
</div>

<!-- Subway section - make it a container -->
<section class="subway-section">
    <h2>🚇 SUBWAY</h2>
    <div data-subway-container>
        <!-- Will be populated by JavaScript -->
        <p class="loading">Loading subway data...</p>
    </div>
</section>

<!-- Citibike section -->
<section class="citibike-section">
    <h2>🚲 CITIBIKE</h2>
    <div data-citibike-container>
        <!-- Will be populated by JavaScript -->
        <p class="loading">Loading Citibike data...</p>
    </div>
</section>

<!-- Add script tag before </body> -->
<script src="app.js"></script>
```

---

### 2. Create `frontend/app.js` - Main Application

#### Core Structure
```javascript
// Configuration
const API_BASE = window.location.origin; // http://localhost:5000
const REFRESH_INTERVAL = 15000; // 15 seconds
const STALENESS_WARNING = 60;   // 60 seconds
const STALENESS_CRITICAL = 120; // 120 seconds

// State management
let lastFetchTime = null;
let fetchErrorCount = 0;

// DOM element references (cached for performance)
const subwayContainer = document.querySelector('[data-subway-container]');
const citibikeContainer = document.querySelector('[data-citibike-container]');
const stalenessDot = document.querySelector('[data-staleness-dot]');
const stalenessText = document.querySelector('[data-staleness-text]');

// Main fetch and update functions
async function fetchSubwayData() { /* ... */ }
async function fetchCitibikeData() { /* ... */ }
async function fetchHealthData() { /* ... */ }

function updateSubwayDisplay(data) { /* ... */ }
function updateCitibikeDisplay(data) { /* ... */ }
function updateStalenessIndicator(seconds) { /* ... */ }

// Initialize
function init() {
    fetchAllData();
    setInterval(fetchAllData, REFRESH_INTERVAL);
}

// Start on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
```

---

### 3. Implement Fetch Functions

#### Fetch Subway Data
```javascript
async function fetchSubwayData() {
    try {
        const response = await fetch(`${API_BASE}/api/subway`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const json = await response.json();
        if (json.success) {
            updateSubwayDisplay(json.data);
            lastFetchTime = Date.now();
            fetchErrorCount = 0;
        }
    } catch (error) {
        console.error('Subway fetch failed:', error);
        fetchErrorCount++;
        showError(subwayContainer, 'Unable to load subway data');
    }
}
```

#### Fetch Citibike Data
```javascript
async function fetchCitibikeData() {
    try {
        const response = await fetch(`${API_BASE}/api/citibike`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const json = await response.json();
        if (json.success) {
            updateCitibikeDisplay(json.data);
        }
    } catch (error) {
        console.error('Citibike fetch failed:', error);
        showError(citibikeContainer, 'Unable to load Citibike data');
    }
}
```

#### Fetch Health Data (for staleness)
```javascript
async function fetchHealthData() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const json = await response.json();
        
        // Calculate staleness from subway data (most frequently updated)
        const subwayAge = json.subway?.last_update || 'unknown';
        updateStalenessIndicator(subwayAge);
    } catch (error) {
        console.error('Health fetch failed:', error);
    }
}
```

#### Fetch All Data
```javascript
async function fetchAllData() {
    await Promise.all([
        fetchSubwayData(),
        fetchCitibikeData(),
        fetchHealthData()
    ]);
}
```

---

### 4. Implement Display Update Functions

#### Update Subway Display
```javascript
function updateSubwayDisplay(arrivals) {
    // Group arrivals by station
    const grouped = groupByStation(arrivals);
    
    // Generate HTML
    const html = Object.entries(grouped).map(([station, trains]) => {
        const lines = [...new Set(trains.map(t => t.line))]; // Unique lines
        
        return `
            <div class="station-group">
                <div class="station-header">
                    <div class="line-badges">
                        ${lines.map(line => 
                            `<span class="line-badge line-${line.toLowerCase()}">${line}</span>`
                        ).join('')}
                    </div>
                    <span class="station-name">${station}</span>
                </div>
                <div class="arrivals">
                    ${trains.slice(0, 2).map(train => `
                        <div class="arrival ${getUrgencyClass(train.minutes_until)}">
                            <span class="line-indicator line-${train.line.toLowerCase()}">${train.line}</span>
                            <span class="time">${formatMinutes(train.minutes_until)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }).join('');
    
    subwayContainer.innerHTML = html || '<p class="no-data">No trains scheduled</p>';
}

// Helper: Group arrivals by station name
function groupByStation(arrivals) {
    return arrivals.reduce((acc, arrival) => {
        const key = arrival.station;
        if (!acc[key]) acc[key] = [];
        acc[key].push(arrival);
        return acc;
    }, {});
}

// Helper: Format minutes display
function formatMinutes(minutes) {
    if (minutes <= 0) return 'Now';
    if (minutes === 1) return '1 min';
    return `${minutes} min`;
}

// Helper: Get urgency CSS class
function getUrgencyClass(minutes) {
    if (minutes <= 1) return 'urgent'; // Red
    if (minutes <= 3) return 'soon';   // Yellow
    return '';                          // Default
}
```

#### Update Citibike Display
```javascript
function updateCitibikeDisplay(stations) {
    const html = stations.map(station => {
        const percentFull = station.percent_full || 0;
        const isCritical = percentFull >= 90 || percentFull <= 10;
        
        return `
            <div class="citibike-station">
                <h3 class="dock-name">${station.name}</h3>
                <div class="dock-status">
                    <div class="progress-bar">
                        <div class="progress-fill ${isCritical ? 'critical' : ''}" 
                             style="width: ${percentFull}%">
                        </div>
                    </div>
                    <div class="dock-counts">
                        <span class="bike-count">
                            🚲 ${station.bikes_available} bikes
                            ${station.ebikes_available > 0 ? ` (⚡${station.ebikes_available})` : ''}
                        </span>
                        <span class="dock-count">
                            🅿 ${station.docks_available} docks
                        </span>
                    </div>
                    ${!station.is_renting ? '<p class="warning">⚠ Not renting</p>' : ''}
                    ${!station.is_returning ? '<p class="warning">⚠ Not accepting returns</p>' : ''}
                </div>
            </div>
        `;
    }).join('');
    
    citibikeContainer.innerHTML = html || '<p class="no-data">No stations configured</p>';
}
```

#### Update Staleness Indicator
```javascript
function updateStalenessIndicator(ageString) {
    // Parse "30s ago" or "2m ago" format from health API
    const seconds = parseAgeString(ageString);
    
    let statusClass = 'healthy';
    let statusText = `Updated ${ageString}`;
    
    if (seconds > STALENESS_CRITICAL) {
        statusClass = 'critical';
        statusText = `⚠ Data stale (${ageString})`;
    } else if (seconds > STALENESS_WARNING) {
        statusClass = 'warning';
        statusText = `⚠ Data aging (${ageString})`;
    }
    
    stalenessDot.className = `staleness-dot ${statusClass}`;
    stalenessText.textContent = statusText;
}

// Helper: Parse "30s ago" or "2m ago" to seconds
function parseAgeString(str) {
    const match = str.match(/(\d+)([sm])/);
    if (!match) return 0;
    
    const value = parseInt(match[1]);
    const unit = match[2];
    
    return unit === 'm' ? value * 60 : value;
}
```

---

### 5. Error Handling

#### Show Error Message
```javascript
function showError(container, message) {
    container.innerHTML = `
        <div class="error-message">
            <p>❌ ${message}</p>
            <p class="error-hint">Retrying automatically...</p>
        </div>
    `;
}
```

#### Add Error Styles to CSS
```css
.error-message {
    padding: 30px;
    text-align: center;
    color: #ff6666;
    background: #331111;
    border-radius: 8px;
}

.error-hint {
    font-size: 14px;
    color: #999;
    margin-top: 10px;
}

.loading {
    text-align: center;
    color: #999;
    font-style: italic;
}

.no-data {
    text-align: center;
    color: #666;
    padding: 20px;
}
```

---

### 6. Visual Urgency Classes

Add to `style.css`:
```css
/* Urgent arrivals (≤1 min) */
.arrival.urgent .time {
    color: #ff4444;
    animation: pulse 1s infinite;
}

/* Soon arrivals (≤3 min) */
.arrival.soon .time {
    color: #ffaa00;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

/* Critical dock levels */
.progress-fill.critical {
    background: linear-gradient(90deg, #ff4444, #cc0000);
}

.warning {
    color: #ffaa00;
    font-size: 14px;
    margin-top: 8px;
}
```

---

## Requirements

### Performance
- Cache DOM queries (don't query on every update)
- Use `innerHTML` for bulk updates (faster than createElement loops)
- Debounce rapid fetches if backend is slow

### Error Recovery
- Don't clear existing data on fetch error
- Show last known good data with warning
- Auto-retry after 15 seconds
- Log errors to console for debugging

### Data Validation
- Check `json.success` before using data
- Handle missing fields gracefully
- Validate arrival times (no negative minutes)
- Validate dock percentages (0-100%)

---

## Acceptance Criteria
- [ ] Dashboard fetches data immediately on page load
- [ ] Auto-refreshes every 15 seconds
- [ ] Subway arrivals display and update correctly
- [ ] Citibike status displays with progress bars
- [ ] Staleness indicator changes color based on data age
- [ ] Urgent trains (≤1 min) pulse in red
- [ ] Full/empty docks show critical state
- [ ] Network errors don't crash the page
- [ ] Last good data persists during errors
- [ ] No console errors in normal operation

---

## Testing Checklist

### 1. Normal operation
```bash
# Start backend
python backend/app.py

# Open frontend
# http://localhost:5000

# Check:
# - Data loads within 2 seconds
# - Staleness indicator is green
# - Train times match MTA app
# - Citibike counts match Citibike app
```

### 2. Auto-refresh
```bash
# Watch dashboard for 2 minutes
# Data should update every 15 seconds
# Check browser network tab for fetch requests
```

### 3. Network failure simulation
```bash
# Stop Flask server while dashboard is running
# Dashboard should:
#   - Show last known data
#   - Staleness indicator turns red
#   - No console errors
#   - Auto-recovers when server restarts
```

### 4. Edge cases
Test with these data scenarios:
- No trains scheduled (late night)
- Train arriving "now" (0 minutes)
- All docks full (100%)
- All bikes taken (0%)
- Station offline (is_renting = false)

### 5. Browser compatibility
Test in:
- Chrome/Chromium (target for Pi)
- Safari (dev on Mac)
- Firefox (backup)

---

## Console Logging (Debug Mode)

Add helpful logs during development:
```javascript
function fetchAllData() {
    console.log('[Dashboard] Fetching data...');
    
    Promise.all([...]).then(() => {
        console.log('[Dashboard] Fetch complete');
    });
}
```

Remove or comment out before deploying to Pi.

---

## Deliverables
After this session:
1. `frontend/app.js` with complete fetch/update logic
2. Updated `frontend/index.html` with data attributes
3. Updated `frontend/style.css` with urgency states
4. Fully functional dashboard at `http://localhost:5000`

The dashboard should now show **live, auto-updating transit data** without any user interaction.

---

## Next Session
Session 5 (Testing) is your job - run this dashboard for real during your morning commute and document any bugs or UX issues.

Session 6 (Raspberry Pi Deployment) will use this completed frontend.

---

## Reference Links
- Fetch API: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API
- DOM manipulation: https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model
- Async/await: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function
- CSS animations: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations
