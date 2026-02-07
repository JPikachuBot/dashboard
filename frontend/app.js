const API_BASE = window.location.origin;

const DEFAULT_REFRESH_INTERVAL_MS = 15000;
const DEFAULT_STALENESS_WARNING_SEC = 60;
const DEFAULT_STALENESS_CRITICAL_SEC = 120;

const subwayContainer = document.querySelector('[data-subway-container]');
const citibikeContainer = document.querySelector('[data-citibike-container]');
const stalenessDot = document.querySelector('[data-staleness-dot]');
const stalenessText = document.querySelector('[data-staleness-text]');

const configElement = document.body;
const refreshIntervalMs = parsePositiveInt(
    configElement?.dataset.refreshIntervalMs,
    DEFAULT_REFRESH_INTERVAL_MS,
);
const stalenessWarningSec = parsePositiveInt(
    configElement?.dataset.stalenessWarningSec,
    DEFAULT_STALENESS_WARNING_SEC,
);
const stalenessCriticalSec = parsePositiveInt(
    configElement?.dataset.stalenessCriticalSec,
    DEFAULT_STALENESS_CRITICAL_SEC,
);

let lastSubwayMarkup = '';
let lastCitibikeMarkup = '';
let inFlight = false;
let refreshTimerId = null;
let lastStalenessSeconds = null;

function parsePositiveInt(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed) || parsed <= 0) {
        return fallback;
    }
    return parsed;
}

function clampNumber(value, min, max) {
    const num = Number(value);
    if (Number.isNaN(num)) {
        return min;
    }
    return Math.min(max, Math.max(min, num));
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function normalizeLineClass(line) {
    return String(line).toLowerCase().replace(/[^a-z0-9]/g, '');
}

function formatMinutes(minutes) {
    if (minutes <= 0) return 'Now';
    if (minutes === 1) return '1 min';
    return `${minutes} min`;
}

function getUrgencyClass(minutes) {
    if (minutes <= 1) return 'urgent';
    if (minutes <= 3) return 'soon';
    return '';
}

function groupByStation(arrivals) {
    return arrivals.reduce((acc, arrival) => {
        const station = arrival.station || 'Unknown station';
        if (!acc[station]) {
            acc[station] = [];
        }
        acc[station].push(arrival);
        return acc;
    }, {});
}

function buildSubwayMarkup(arrivals) {
    if (!Array.isArray(arrivals)) {
        return '<p class="no-data">No trains scheduled</p>';
    }

    const sanitizedArrivals = arrivals
        .map((arrival) => {
            const minutes = clampNumber(arrival.minutes_until, 0, 9999);
            return {
                line: arrival.line || '?',
                station: arrival.station || 'Unknown station',
                minutes_until: minutes,
            };
        })
        .filter((arrival) => arrival.station);

    if (sanitizedArrivals.length === 0) {
        return '<p class="no-data">No trains scheduled</p>';
    }

    const grouped = groupByStation(sanitizedArrivals);

    return Object.entries(grouped)
        .map(([station, trains]) => {
            const lines = Array.from(new Set(trains.map((train) => train.line)));
            const lineBadges = lines
                .map((line) => {
                    const lineClass = normalizeLineClass(line);
                    return `<span class="line-badge line-${lineClass}">${escapeHtml(line)}</span>`;
                })
                .join('');

            const arrivalsHtml = trains
                .slice(0, 2)
                .map((train) => {
                    const lineClass = normalizeLineClass(train.line);
                    const minutes = clampNumber(train.minutes_until, 0, 9999);
                    const urgencyClass = getUrgencyClass(minutes);
                    return `
                        <div class="arrival ${urgencyClass}">
                            <span class="line-indicator line-${lineClass}">${escapeHtml(train.line)}</span>
                            <span class="time">${formatMinutes(minutes)}</span>
                        </div>
                    `;
                })
                .join('');

            return `
                <div class="station-group">
                    <div class="station-header">
                        <div class="line-badges">
                            ${lineBadges}
                        </div>
                        <span class="station-name">${escapeHtml(station)}</span>
                    </div>
                    <div class="arrivals">
                        ${arrivalsHtml}
                    </div>
                </div>
            `;
        })
        .join('');
}

function buildCitibikeMarkup(stations) {
    if (!Array.isArray(stations) || stations.length === 0) {
        return '<p class="no-data">No stations configured</p>';
    }

    return stations
        .map((station) => {
            const percentFull = clampNumber(station.percent_full, 0, 100);
            const isCritical = percentFull >= 90 || percentFull <= 10;
            const name = station.name || 'Unknown station';
            const bikesAvailable = clampNumber(station.bikes_available, 0, 9999);
            const ebikesAvailable = clampNumber(station.ebikes_available, 0, 9999);
            const docksAvailable = clampNumber(station.docks_available, 0, 9999);
            const isRenting = station.is_renting !== false;
            const isReturning = station.is_returning !== false;

            return `
                <div class="citibike-station">
                    <h3 class="dock-name">${escapeHtml(name)}</h3>
                    <div class="dock-status">
                        <div class="progress-bar">
                            <div class="progress-fill ${isCritical ? 'critical' : ''}" style="width: ${percentFull}%"></div>
                        </div>
                        <div class="dock-counts">
                            <span class="bike-count">
                                🚲 ${bikesAvailable} bikes${ebikesAvailable > 0 ? ` (⚡${ebikesAvailable})` : ''}
                            </span>
                            <span class="dock-count">🅿 ${docksAvailable} docks</span>
                        </div>
                        ${!isRenting ? '<p class="warning">⚠ Not renting</p>' : ''}
                        ${!isReturning ? '<p class="warning">⚠ Not accepting returns</p>' : ''}
                    </div>
                </div>
            `;
        })
        .join('');
}

function setStalenessStatus(statusClass, text) {
    if (stalenessDot) {
        stalenessDot.className = `staleness-dot ${statusClass}`.trim();
    }
    if (stalenessText) {
        stalenessText.textContent = text;
    }
}

function formatAge(seconds) {
    if (seconds < 60) {
        return `${seconds}s ago`;
    }
    const minutes = Math.round(seconds / 60);
    return `${minutes}m ago`;
}

function parseAgeString(value) {
    if (!value || typeof value !== 'string') {
        return null;
    }
    if (value.trim().toLowerCase() === 'never') {
        return null;
    }
    const match = value.match(/(\d+)\s*([smh])/i);
    if (!match) {
        return null;
    }
    const amount = Number.parseInt(match[1], 10);
    if (Number.isNaN(amount)) {
        return null;
    }
    const unit = match[2].toLowerCase();
    if (unit === 'h') {
        return amount * 3600;
    }
    if (unit === 'm') {
        return amount * 60;
    }
    return amount;
}

function updateStalenessIndicator(seconds, ageString = null) {
    if (seconds == null) {
        setStalenessStatus('critical', '⚠ Data age unavailable');
        return;
    }

    const safeSeconds = clampNumber(seconds, 0, Number.MAX_SAFE_INTEGER);
    lastStalenessSeconds = safeSeconds;
    const label = ageString || formatAge(safeSeconds);

    let statusClass = 'healthy';
    let statusText = `Updated ${label}`;

    if (safeSeconds >= stalenessCriticalSec) {
        statusClass = 'critical';
        statusText = `⚠ Data stale (${label})`;
    } else if (safeSeconds >= stalenessWarningSec) {
        statusClass = 'warning';
        statusText = `⚠ Data aging (${label})`;
    }

    setStalenessStatus(statusClass, statusText);
}

function renderError(container, message, lastMarkup) {
    if (!container) {
        return;
    }
    const errorMarkup = `
        <div class="error-message">
            <p>❌ ${escapeHtml(message)}</p>
            <p class="error-hint">Retrying automatically...</p>
        </div>
    `;

    if (lastMarkup) {
        container.innerHTML = `${errorMarkup}${lastMarkup}`;
    } else {
        container.innerHTML = errorMarkup;
    }
}

async function fetchSubwayData() {
    if (!subwayContainer) {
        return;
    }
    try {
        const response = await fetch(`${API_BASE}/api/subway`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const json = await response.json();
        if (!json || json.success !== true) {
            throw new Error('Unexpected response');
        }
        const markup = buildSubwayMarkup(json.data);
        subwayContainer.innerHTML = markup;
        lastSubwayMarkup = markup;
        if (typeof json.staleness_seconds === 'number') {
            updateStalenessIndicator(json.staleness_seconds);
        }
    } catch (error) {
        console.error('Subway fetch failed:', error);
        renderError(subwayContainer, 'Unable to load subway data', lastSubwayMarkup);
    }
}

async function fetchCitibikeData() {
    if (!citibikeContainer) {
        return;
    }
    try {
        const response = await fetch(`${API_BASE}/api/citibike`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const json = await response.json();
        if (!json || json.success !== true) {
            throw new Error('Unexpected response');
        }
        const markup = buildCitibikeMarkup(json.data);
        citibikeContainer.innerHTML = markup;
        lastCitibikeMarkup = markup;
    } catch (error) {
        console.error('Citibike fetch failed:', error);
        renderError(citibikeContainer, 'Unable to load Citibike data', lastCitibikeMarkup);
    }
}

async function fetchHealthData() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const json = await response.json();
        const ageString = json?.subway?.last_update;
        const parsedSeconds = parseAgeString(ageString);
        if (parsedSeconds !== null) {
            updateStalenessIndicator(parsedSeconds, ageString);
        }
    } catch (error) {
        console.error('Health fetch failed:', error);
        if (lastStalenessSeconds !== null) {
            updateStalenessIndicator(lastStalenessSeconds + Math.round(refreshIntervalMs / 1000));
        }
    }
}

async function fetchAllData() {
    if (inFlight) {
        scheduleNextFetch();
        return;
    }
    inFlight = true;
    try {
        await Promise.allSettled([
            fetchSubwayData(),
            fetchCitibikeData(),
            fetchHealthData(),
        ]);
    } finally {
        inFlight = false;
        scheduleNextFetch();
    }
}

function scheduleNextFetch() {
    if (refreshTimerId) {
        clearTimeout(refreshTimerId);
    }
    refreshTimerId = setTimeout(fetchAllData, refreshIntervalMs);
}

function init() {
    setStalenessStatus('warning', 'Updating...');
    fetchAllData();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
