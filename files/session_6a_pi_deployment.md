# Session 6A: Raspberry Pi Deployment Scripts

## Context
You are working on Milestone 6 of the FiDi Transit Dashboard project. The dashboard works on your Mac Mini. This session creates deployment scripts and configurations to run it automatically on a Raspberry Pi.

## Files You Need Access To
- `~/Projects/dashboard/deploy/fidi-dash.service` (create - systemd unit)
- `~/Projects/dashboard/deploy/kiosk.sh` (create - Chromium launcher)
- `~/Projects/dashboard/deploy/setup-pi.sh` (create - one-shot Pi setup)
- `~/Projects/dashboard/deploy/config-display.txt` (create - HDMI config notes)

## Background
The Raspberry Pi needs to:
1. **Auto-start Flask** on boot (as a systemd service)
2. **Auto-launch Chromium** in kiosk mode pointing to localhost:5000
3. **Rotate display** to portrait orientation (90°)
4. **Disable screen blanking** (runs 24/7)
5. **Auto-login** as user `pi` (no password prompt)
6. **Auto-recover** from crashes (systemd restarts)

**Target Pi OS:** Raspberry Pi OS (Debian Bookworm) - latest as of Feb 2026

---

## Your Task

### 1. Create `deploy/fidi-dash.service` - Systemd Service

This runs the Flask backend as a system service:

```ini
[Unit]
Description=FiDi Transit Dashboard Backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/dashboard
Environment="PATH=/home/pi/dashboard/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/pi/dashboard/venv/bin/python /home/pi/dashboard/backend/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits (optional, for stability)
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

**Key features:**
- Runs as user `pi` (not root)
- Uses virtual environment Python
- Auto-restarts on crash (10s delay)
- Waits for network before starting
- Logs to journalctl
- Memory limit prevents OOM crashes

---

### 2. Create `deploy/kiosk.sh` - Chromium Kiosk Launcher

This script launches Chromium in fullscreen kiosk mode:

```bash
#!/bin/bash
# Chromium Kiosk Mode Launcher
# Waits for Flask to be ready, then opens dashboard

# Wait for Flask backend to be responsive
echo "Waiting for Flask backend..."
until curl -s http://localhost:5000/api/health > /dev/null; do
    echo "Backend not ready, retrying in 2s..."
    sleep 2
done

echo "Backend ready! Launching Chromium..."

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Launch Chromium in kiosk mode
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-translate \
    --no-first-run \
    --check-for-update-interval=31536000 \
    --disable-pinch \
    --overscroll-history-navigation=0 \
    http://localhost:5000
```

**Key features:**
- Waits for Flask to be healthy before launching
- Disables all Chromium UI elements
- Disables screen blanking via xset
- Fullscreen, no navigation controls
- No error dialogs or update prompts

---

### 3. Create `deploy/setup-pi.sh` - Automated Setup Script

This script does everything needed to deploy on a fresh Pi:

```bash
#!/bin/bash
# Raspberry Pi Setup Script for FiDi Transit Dashboard
# Run this once on a fresh Pi OS installation

set -e  # Exit on error

echo "======================================"
echo "FiDi Transit Dashboard - Pi Setup"
echo "======================================"
echo ""

# Update system
echo "[1/9] Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install dependencies
echo "[2/9] Installing Python and dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    chromium-browser \
    x11-xserver-utils \
    unclutter

# Clone project (or assume it's already there)
echo "[3/9] Setting up project directory..."
if [ ! -d "$HOME/dashboard" ]; then
    echo "Cloning project from Git..."
    # git clone YOUR_REPO_URL $HOME/dashboard
    echo "⚠ Manual step: Copy project files to $HOME/dashboard"
else
    echo "Project directory exists, skipping clone"
fi

cd $HOME/dashboard

# Create virtual environment
echo "[4/9] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "[5/9] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install systemd service
echo "[6/9] Installing systemd service..."
sudo cp deploy/fidi-dash.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fidi-dash.service
sudo systemctl start fidi-dash.service

echo "Backend service status:"
sudo systemctl status fidi-dash.service --no-pager

# Configure auto-login
echo "[7/9] Configuring auto-login..."
sudo raspi-config nonint do_boot_behaviour B4  # Desktop autologin

# Configure autostart (launch kiosk on login)
echo "[8/9] Configuring Chromium autostart..."
mkdir -p $HOME/.config/autostart
cat > $HOME/.config/autostart/fidi-dash.desktop << EOF
[Desktop Entry]
Type=Application
Name=FiDi Dashboard Kiosk
Exec=/home/pi/dashboard/deploy/kiosk.sh
X-GNOME-Autostart-enabled=true
EOF

chmod +x deploy/kiosk.sh

# Disable screen blanking (LXDE config)
echo "[9/9] Disabling screen blanking..."
mkdir -p $HOME/.config/lxsession/LXDE-pi
cat > $HOME/.config/lxsession/LXDE-pi/autostart << EOF
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@point-rpi
@xset s off
@xset -dpms
@xset s noblank
@/home/pi/dashboard/deploy/kiosk.sh
EOF

echo ""
echo "======================================"
echo "✅ Setup complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Configure display rotation (see deploy/config-display.txt)"
echo "2. Edit config.yaml for your stations"
echo "3. Reboot the Pi: sudo reboot"
echo ""
echo "The dashboard will auto-start after reboot."
```

---

### 4. Create `deploy/config-display.txt` - Display Configuration Guide

This is a reference document for rotating the display:

```text
RASPBERRY PI DISPLAY CONFIGURATION
===================================

PORTRAIT MODE (90° ROTATION)
----------------------------

Method 1: Using Raspberry Pi Configuration Tool
```bash
sudo raspi-config
# Navigate to: Display Options > Screen Blanking > No
# Navigate to: Display Options > Screen Resolution (choose 1080x1920)
# For rotation: Need to edit config.txt manually (see below)
```

Method 2: Edit /boot/firmware/config.txt (or /boot/config.txt on older Pi OS)
```bash
sudo nano /boot/firmware/config.txt

# Add this line for 90° clockwise rotation (portrait):
display_rotate=1

# Other rotation options:
# display_rotate=0  # Normal (landscape)
# display_rotate=1  # 90° clockwise (portrait - recommended)
# display_rotate=2  # 180° (upside down)
# display_rotate=3  # 270° clockwise (portrait, inverted)

# Save and reboot:
sudo reboot
```

DISABLE SCREEN BLANKING
------------------------
Already handled by kiosk.sh and autostart config, but verify with:
```bash
xset q | grep "DPMS"
# Should show: DPMS is Disabled
```

RESOLUTION DETECTION
--------------------
Check current resolution:
```bash
xrandr
# Look for current resolution (e.g., 1080x1920 if portrait)
```

TROUBLESHOOTING
---------------
1. Display is rotated wrong way:
   - Try display_rotate=3 instead of 1

2. Screen still blanks after 10 minutes:
   - Verify kiosk.sh is running: ps aux | grep chromium
   - Check autostart file: cat ~/.config/lxsession/LXDE-pi/autostart

3. Resolution is wrong:
   - Edit config.txt and add: hdmi_group=2, hdmi_mode=82
   - Full list: https://www.raspberrypi.com/documentation/computers/config_txt.html

4. Touch input not rotated (if using touchscreen):
   - Add to config.txt: dtoverlay=rpi-ft5406,touchscreen-swapped-x-y

RECOMMENDED CONFIG.TXT SETTINGS
--------------------------------
```
# HDMI output
hdmi_force_hotplug=1
hdmi_drive=2

# Portrait rotation
display_rotate=1

# Disable rainbow splash
disable_splash=1

# Disable boot text
boot_delay=0
```
```

---

## Requirements

### Security
- Service runs as non-root user (`pi`)
- No hardcoded passwords
- Minimal permissions

### Reliability
- Auto-restart on crash (systemd)
- Wait for network before starting
- Graceful failure if backend unreachable

### Maintenance
- Logs accessible via `journalctl -u fidi-dash -f`
- Easy to update: `git pull && sudo systemctl restart fidi-dash`
- Config changes don't require service modification

---

## Acceptance Criteria
- [ ] systemd service file is valid and installable
- [ ] kiosk.sh script launches Chromium correctly
- [ ] setup-pi.sh runs without errors on fresh Pi OS
- [ ] Display rotation guide is clear and accurate
- [ ] All scripts are executable (`chmod +x`)
- [ ] Backend auto-starts on boot
- [ ] Chromium auto-launches in kiosk mode
- [ ] Screen doesn't blank during operation
- [ ] Service survives reboot

---

## Testing Checklist (Do on Actual Pi)

### Before running setup:
```bash
# Flash fresh Pi OS to SD card
# Boot Pi, complete initial setup (WiFi, user, etc.)
# Copy project to Pi via git or scp
```

### Run setup:
```bash
cd ~/dashboard
chmod +x deploy/setup-pi.sh
./deploy/setup-pi.sh

# Watch for errors
# Note any missing dependencies
```

### Verify systemd service:
```bash
# Check status
sudo systemctl status fidi-dash

# View logs
journalctl -u fidi-dash -f

# Test restart
sudo systemctl restart fidi-dash

# Check it's serving
curl http://localhost:5000/api/health
```

### Verify kiosk mode:
```bash
# Reboot to test autostart
sudo reboot

# After reboot, check:
# - Chromium opens automatically
# - Shows dashboard at localhost:5000
# - No UI chrome (address bar, etc.)
# - Display is portrait orientation

# Verify screen blanking disabled
xset q | grep "DPMS"
```

### Test failure recovery:
```bash
# Kill backend process
sudo pkill -f app.py

# Wait 10 seconds
# systemd should auto-restart it

# Check it restarted
sudo systemctl status fidi-dash
```

---

## Manual Deployment Steps (Reference)

If setup-pi.sh fails, do these steps manually:

1. **Copy project to Pi:**
   ```bash
   scp -r ~/Projects/dashboard pi@raspberrypi.local:~/
   ```

2. **On Pi, install dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3-venv chromium-browser
   ```

3. **Set up venv and install packages:**
   ```bash
   cd ~/dashboard
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Install systemd service:**
   ```bash
   sudo cp deploy/fidi-dash.service /etc/systemd/system/
   sudo systemctl enable fidi-dash
   sudo systemctl start fidi-dash
   ```

5. **Configure autostart:**
   ```bash
   mkdir -p ~/.config/autostart
   cp deploy/fidi-dash.desktop ~/.config/autostart/
   chmod +x deploy/kiosk.sh
   ```

6. **Rotate display:**
   ```bash
   sudo nano /boot/firmware/config.txt
   # Add: display_rotate=1
   sudo reboot
   ```

---

## Deliverables
After this session:
1. `deploy/fidi-dash.service` - systemd unit file
2. `deploy/kiosk.sh` - Chromium launcher script
3. `deploy/setup-pi.sh` - Automated setup script
4. `deploy/config-display.txt` - Display config reference

These files make deploying to a fresh Pi a 5-minute process.

---

## Next Steps (After Deployment)
- Milestone 7: Use the deployed dashboard for 3+ days
- Document any crashes, stale data, or UX issues
- Tweak font sizes if needed (view from actual distance)
- Update STATUS.md with deployment notes

---

## Reference Links
- systemd service files: https://www.freedesktop.org/software/systemd/man/systemd.service.html
- Raspberry Pi config.txt: https://www.raspberrypi.com/documentation/computers/config_txt.html
- Chromium kiosk mode: https://die-antwort.eu/techblog/2017-12-setup-raspberry-pi-for-kiosk-mode/
- Screen blanking on Pi: https://www.raspberrypi.com/documentation/computers/configuration.html
