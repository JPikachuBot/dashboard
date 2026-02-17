# Backups

This project uses git for versioned history. In addition, we sometimes create **git bundle** artifacts as offline backups of unpushed commits.

## 2026-02-16 — Inbound tracker + layout updates

Created local commits:
- `149ae108cc83dff7ec4cc0b06bfce6e8e3a7f8be` — `feat: inbound tracker 2-section format + inward-aligned station rows`
- `adc34d3` — `ui: keep Uptown/Downtown headers; add direction sublabels`

Created offline git bundle backups (diff vs `origin/main` at time of creation):
- `~/.openclaw/workspace/backups/dashboard-149ae10.bundle`
- `~/.openclaw/workspace/backups/dashboard-adc34d3.bundle`

Notes:
- Bundles can be inspected with `git bundle list-heads <file>` and applied by cloning/fetching from the bundle.
- These backups do **not** replace pushing to a remote; they’re an extra safety net when work is ahead of `origin/main`.
