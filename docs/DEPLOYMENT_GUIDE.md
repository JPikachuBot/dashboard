# FiDi Dash — Deployment Guide

**Date:** February 15, 2026
**Setup:** Mac Mini (server) → iPad (wall display)
**Network:** Mac Mini on Ethernet, iPad on WiFi, same local network

---

## Overview

The dashboard is already running at `http://127.0.0.1:5000/`. Deployment means two things:

1. Make it accessible on the local network so the iPad can reach it
2. Lock the iPad into a kiosk displaying the dashboard

No Raspberry Pi, no cloud, no Docker. The Mac Mini serves; the iPad displays.

---

## Part 1: Mac Mini — Network & Persistence

> **These steps should be executed on the Mac Mini.**

### 1.1 Bind Flask to the Local Network

The Flask app should listen on all network interfaces by default, with an override available when needed.

**Current behavior in `backend/app.py`:**

- Default bind: `HOST=0.0.0.0`, `PORT=5000`
- Override example (localhost only): `HOST=127.0.0.1 PORT=5000`

### 1.2 Find the Mac Mini's Local IP

Run this in Terminal:

```bash
ipconfig getifaddr en0
```

This returns something like `192.168.1.XX`. That's the dashboard URL:

```
http://192.168.1.XX:5000
```

**Test it:** Open that URL from any other device on your network (phone, iPad, laptop). You should see the dashboard.

### 1.3 Assign a Static IP (Prevents the URL from Changing)

Your router may reassign the Mac Mini's IP address over time, which would break the iPad's bookmark.

**Option A — Set static IP on Mac Mini (recommended):**

1. Open **System Settings → Network → Ethernet → Details → TCP/IP**
2. Change "Configure IPv4" from "Using DHCP" to **"Manually"**
3. Set:
   - **IP Address:** Your current IP from step 1.2 (e.g., `192.168.1.XX`)
   - **Subnet Mask:** `255.255.255.0`
   - **Router:** Your router's IP (usually `192.168.1.1`)
4. Go to **DNS** tab and add `8.8.8.8` and `8.8.4.4` (Google DNS)
5. Click **OK**

**Option B — DHCP reservation in your router:**

Log into your router's admin page (usually `192.168.1.1`), find DHCP settings, and reserve the Mac Mini's current IP by its MAC address. This varies by router model.

### 1.4 Keep Flask Running Persistently

You need Flask to run in the background and survive reboots.

**Use the LaunchAgent plist in this repo:**

The file `docs/com.fididash.server.plist` is already configured with the correct paths for this repo:

- Python: `/Users/jacksonbutler/Projects/dashboard/venv/bin/python`
- App: `/Users/jacksonbutler/Projects/dashboard/backend/app.py`
- Working directory: `/Users/jacksonbutler/Projects/dashboard`
- Environment: `HOST=0.0.0.0`, `PORT=5000`

**Install it:**

```bash
cp /Users/jacksonbutler/Projects/dashboard/docs/com.fididash.server.plist ~/Library/LaunchAgents/com.fididash.server.plist
```

**Load it:**

```bash
launchctl load ~/Library/LaunchAgents/com.fididash.server.plist
```

**Verify it's running:**

```bash
launchctl list | grep fididash
```

**To stop/restart:**

```bash
launchctl unload ~/Library/LaunchAgents/com.fididash.server.plist
launchctl load ~/Library/LaunchAgents/com.fididash.server.plist
```

**To check logs:**

```bash
tail -f /tmp/fidi-dash.log
tail -f /tmp/fidi-dash-error.log
```

This will auto-start on login and auto-restart if the process crashes.

---

## Part 2: iPad — Kiosk Setup

> **These steps are performed on the iPad.**

### 2.1 Open the Dashboard in Safari

Navigate to:

```
http://192.168.1.XX:5000
```

(Replace with your Mac Mini's actual IP from step 1.2.)

Confirm the dashboard loads and looks correct.

### 2.2 Add to Home Screen

1. Tap the **Share** button (square with upward arrow) in Safari
2. Scroll down and tap **"Add to Home Screen"**
3. Name it **"FiDi Dash"** (or whatever you like)
4. Tap **Add**

This creates a full-screen web app shortcut — no Safari address bar, no tabs, no browser chrome. It looks like a native app.

### 2.3 Disable Auto-Lock

Go to **Settings → Display & Brightness → Auto-Lock → Never**

This keeps the screen on permanently while plugged in.

### 2.4 Enable Guided Access (Kiosk Lock)

1. Go to **Settings → Accessibility → Guided Access**
2. Toggle **Guided Access ON**
3. Tap **Passcode Settings** and set a passcode (you'll need this to exit later)
4. Optionally enable **Face ID** or **Touch ID** for easier unlocking

### 2.5 Launch and Lock

1. Open the **"FiDi Dash"** shortcut from the Home Screen
2. Once the dashboard is displayed, **triple-click the Side Button** (or Home button on older iPads)
3. The Guided Access screen appears — tap **Start** (top right)

The iPad is now locked to the dashboard. No swiping home, no notifications, no accidental exits.

### 2.6 Reduce Brightness for Night (Optional)

Since the dashboard uses a dark theme, screen burn-in and brightness aren't major concerns, but you can:

- **Settings → Display & Brightness → Night Shift** — schedule a warm/dim tone for nighttime
- **Settings → Display & Brightness → Auto-Brightness** — ON, so it dims in a dark room
- Or just set brightness manually to a comfortable level before locking with Guided Access

### 2.7 To Exit Guided Access Later

**Triple-click the Side Button** → enter your passcode → tap **End** (top left).

---

## End-user Testing

> **Do these checks from the iPad after setup.**

### 1) LAN Access Test

1. On the iPad, open Safari and go to `http://192.168.1.XX:5000`
2. Confirm the dashboard loads within a few seconds.
3. Wait for at least one auto-refresh (default 15 seconds) and confirm the page updates without errors.

### 2) Reboot Persistence Test

1. Reboot the Mac Mini.
2. Log in to the Mac Mini (LaunchAgents run on user login).
3. Wait ~30–60 seconds for the service to start.
4. On the iPad, reload `http://192.168.1.XX:5000` and confirm the dashboard is reachable again.

---

## Part 3: Physical Installation

> **Manual steps — no code involved.**

### 3.1 Mounting

- Use a **Command Strip** to mount the iPad to the wall by the door
- Position it at eye level, slightly angled if possible
- Leave space for the charging cable to route downward

### 3.2 Power

- Run a **Lightning or USB-C cable** (depending on your iPad model) from the iPad down to the outlet
- Use a cable channel or cord cover along the wall for a clean look (optional)
- A right-angle cable adapter can help the cable sit flush against the wall

### 3.3 Recommended Position

- **By the front door** so you glance at it on your way out
- Avoid direct sunlight (washes out the screen and heats the iPad)
- Ensure the iPad is within WiFi range of your router

### 3.4 Ongoing Maintenance

- The iPad will stay charged continuously while plugged in — this is fine for modern iPads with battery management
- If the dashboard ever goes blank or shows errors, check:
  1. Is the Mac Mini on? (power outage, sleep, etc.)
  2. Is Flask running? (`launchctl list | grep fididash` on the Mac Mini)
  3. Is the iPad still on WiFi?
- To update the dashboard code, just update it on the Mac Mini — the iPad will pick up changes on its next auto-refresh cycle (every 15 seconds per the config)

---

## Quick Reference

| Component | Detail |
|---|---|
| Dashboard URL | `http://192.168.1.XX:5000` |
| Mac Mini service | `~/Library/LaunchAgents/com.fididash.server.plist` |
| Service logs | `/tmp/fidi-dash.log` and `/tmp/fidi-dash-error.log` |
| iPad kiosk exit | Triple-click Side Button → enter passcode |
| Flask bind address | `0.0.0.0:5000` |
| Frontend refresh | Every 15 seconds (automatic) |

---

## Checklist

- [ ] Flask binds to `0.0.0.0:5000`
- [ ] Mac Mini has a static IP or DHCP reservation
- [ ] Dashboard accessible from iPad via `http://<ip>:5000`
- [ ] Launch Agent created and loaded (auto-start + auto-restart)
- [ ] iPad: shortcut added to Home Screen
- [ ] iPad: Auto-Lock set to Never
- [ ] iPad: Guided Access enabled and locked
- [ ] iPad mounted on wall with Command Strip
- [ ] iPad plugged into power
- [ ] Verified dashboard survives Mac Mini reboot
