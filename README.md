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
Clone
git clone <YOUR_REPO_URL> File-Integrity-Monitor
cd File-Integrity-Monitor

# Create & activate venv (recommended)
python3 -m venv fvenv
source fvenv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install PyYAML Jinja2
```
