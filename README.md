# FIMLite — File Integrity Monitor (Lightweight)

A small, practical tool to detect unauthorized changes to files.

- Creates a **baseline** of file metadata (path, size, SHA-256, mtime) for a chosen folder.
- Later **scans** compare current state to baseline and report **added / removed / modified** files.
- For small text files, generates **unified diffs** and links them in an **HTML report**.
- Configurable via **YAML**, stores data in **SQLite**, and runs from a simple **CLI** (or on a schedule with **cron**).

---

## Features

- YAML config: include/exclude glob rules, severity levels, diff size cap  
- SQLite backend: single file, no server  
- HTML report: clean table + “view diff” links for modified text files  
- CLI flow: `baseline`, `scan`, `select-root`  
- Cron-friendly wrapper script  
- Clear output; easy to extend

---

## Repository Structure

```text
File-Integrity-Monitor/
├─ configs/
│  └─ example.yml                # YAML config (watched folder, rules, paths)
├─ src/
│  └─ fimlite/
│     ├─ __init__.py             # package marker
│     ├─ config.py               # read/validate YAML; ensure output dirs
│     ├─ db.py                   # SQLite schema & helpers (baseline, scans, changes)
│     ├─ walker.py               # walk root; include/exclude; SHA-256/size/mtime
│     ├─ compare.py              # baseline vs current → added/removed/modified
│     ├─ diffing.py              # baseline snapshots & unified diffs
│     ├─ report.py               # render HTML from template (Jinja2)
│     └─ cli.py                  # CLI: baseline / scan / select-root
├─ templates/
│  └─ report.html.j2             # HTML template for scan report
├─ data/                         # (created) SQLite DB files (e.g., fimlite.db)
├─ reports/                      # (created) scan-<id>.html + diffs/
├─ snapshots/                    # (created) baseline file copies for diffing
├─ tests/
│  └─ db_smoketest.py            # simple smoke test for DB layer
├─ bin/
│  └─ fim-scan.sh                # wrapper script for cron (runs a scan)
├─ requirements.txt              # optional: dependency list
└─ README.md                     # this file
```
---

## What each file does

- config.py — loads configs/example.yml, validates paths, creates data/, reports/, snapshots/. Returns a Config.
- db.py — SQLite tables: baseline_files, scans, changes. Read/write baseline; log scans and per-file changes.
- walker.py — walks the watched folder, applies include/exclude, computes size, mtime, sha256.
- compare.py — compares baseline vs current → added / removed / modified list (with severity via glob rules).
- diffing.py — saves baseline snapshots and generates unified diffs for modified text files.
- report.py — renders templates/report.html.j2 → reports/scan-<id>.html.
- cli.py — subcommands: baseline, scan, select-root.
- report.html.j2 — the HTML UI for a scan report.
- fim-scan.sh — cron-friendly script that runs scan with correct env and logs to scan.log.

---
## Requirements

- Python 3.10+
- Recommended: a virtual environment (python3 -m venv fvenv)
- Python packages: PyYAML, Jinja2 (install below)

```Code
# Clone
git clone <YOUR_REPO_URL> File-Integrity-Monitor
cd File-Integrity-Monitor

# Create & activate venv (recommended)
python3 -m venv fvenv
source fvenv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install PyYAML Jinja2
```
## Configuration

Edit configs/example.yml:
```Code
# Folder to monitor (absolute path recommended)
root: "/absolute/path/to/your/folder"

# Output locations (relative to repo root)
db_path: "data/fimlite.db"
report_dir: "reports"
snapshot_dir: "snapshots"

# Include/Exclude patterns (glob; match RELATIVE paths under 'root')
# include: [] means "include everything" (recommended)
include: [] # include: ["*", "**/*"]
exclude:
  - "**/.git/**"
  - "**/__pycache__/**"
  - "**/*.log"
  - "**/node_modules/**"
  - "**/.DS_Store"

# Diff size cap (bytes): skip diff for larger files
max_diff_bytes: 200000

# Severity rules (first match wins)
severity:
  - { pattern: "**/*.sh", level: high }
  - { pattern: "**/*.py", level: medium }
  - { pattern: "**/*",    level: low }
```

## Usage (CLI)

This repo uses a src/ layout. Use PYTHONPATH=src or install the package in editable mode.

1) Choose the folder to monitor (persists in YAML)

```Code
PYTHONPATH=src python3 -m fimlite.cli select-root --config configs/example.yml \
  --path "/absolute/path/to/your/folder"
```
2) Create a baseline (known-good state + snapshots for diffs)

```Code
PYTHONPATH=src python3 -m fimlite.cli baseline --config configs/example.yml
```
3) Make changes inside the watched folder

- Edit a text file → modified (+ diff)
- Add a file → added
- Delete a file → removed

4) Scan and open the report it prints

```Code
PYTHONPATH=src python3 -m fimlite.cli scan --config configs/example.yml
# → prints JSON including: "report": "reports/scan-<ID>.html"

open reports/scan-<ID>.html
```
Important: To see multiple changes in one report, do all edits after baseline and before scan. Re-running baseline resets the reference.

## How It Works

1. Baseline
- Walk folder → record path, size, sha256, mtime in SQLite → snapshot small text files (for diffs).

2. Scan
- Walk again → compare with baseline using SHA-256:
- added: in current, not in baseline
- removed: in baseline, not in current
-  modified: same path, content hash changed
- For modified text files with snapshots and under max_diff_bytes, write a unified diff and link it in the report.

3. Report
- Renders reports/scan-<id>.html with counts and a table; “view diff” opens the .diff file.

Scheduling (cron) — optional

- Run scan automatically (e.g., every 5 minutes).
- Create bin/fim-scan.sh:

```Code
#!/usr/bin/env bash
set -euo pipefail
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$PROJECT/configs/example.yml"
LOG="$PROJECT/scan.log"

# Use venv if present
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  :
elif [[ -f "$PROJECT/fvenv/bin/activate" ]]; then
  source "$PROJECT/fvenv/bin/activate"
elif [[ -f "$PROJECT/.venv/bin/activate" ]]; then
  source "$PROJECT/.venv/bin/activate"
fi

cd "$PROJECT"
echo "[$(date -u +%FT%TZ)] scan start" >> "$LOG"
if PYTHONPATH=src python3 -m fimlite.cli scan --config "$CONFIG" >> "$LOG" 2>&1; then
  echo "[$(date -u +%FT%TZ)] scan end (ok)" >> "$LOG"
else
  echo "[$(date -u +%FT%TZ)] scan end (FAILED)" >> "$LOG"
fi
```
Give Execute Permission
```Code
chmod +x bin/fim-scan.sh
```
Add crontab entries (macOS):

```code
crontab -e
```
Jobs (absolute paths; log both stdout+stderr):

```Code
*/5 * * * * /Users/<your-username>/path/to/File-Integrity-Monitor/bin/fim-scan.sh >> /Users/<your-username>/fim_cron.log 2>&1
* * * * * echo "cron ok $(date)" >> /Users/<your-username>/cron_test.log 2>&1
```

macOS:  Cron doesn’t run while asleep—use launchd for always-on or keep the Mac awake while testing (caffeinate -dimsu &).

## Troubleshooting

- “No changes” after a scan
Ensure you didn’t re-run baseline after editing. Flow: baseline → edit → scan.

- Diff link missing
The file must be text, size ≤ max_diff_bytes, and have a baseline snapshot (snapshots/baseline/<relpath>). Baseline must be run before the edit.

- ModuleNotFoundError: fimlite
Use PYTHONPATH=src or add a pyproject.toml and <run pip install -e .>.

- DB error: “file is not a database”
Rename the bad file and re-init:

```Code
mv data/fimlite.db data/fimlite.db.bak
PYTHONPATH=src python3 -m fimlite.cli baseline --config configs/example.yml
```
## FAQ

### Does FIMLite run continuously in the background?
No. It runs **on demand** (`scan`) or on a **schedule** (via `cron`) to stay simple and light.

### Will it detect changes made outside the CLI?
Yes. Any edits in the watched folder are detected the next time `scan` runs (manual or scheduled).

### How do I switch the monitored folder?
```bash
PYTHONPATH=src python3 -m fimlite.cli select-root --config configs/example.yml --path "/new/folder"
PYTHONPATH=src python3 -m fimlite.cli baseline --config configs/example.yml
```