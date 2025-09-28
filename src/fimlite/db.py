from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, UTC

# SQL that creates our tables
SCHEMA = """
CREATE TABLE IF NOT EXISTS baseline_files (
  path    TEXT PRIMARY KEY,      -- relative path from root
  size    INTEGER NOT NULL,
  sha256  TEXT NOT NULL,
  mtime   REAL NOT NULL          -- modification time (float epoch seconds)
);

CREATE TABLE IF NOT EXISTS scans (
  scan_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,      -- ISO8601 (UTC)
  ended_at   TEXT NOT NULL       -- ISO8601 (UTC)
);

CREATE TABLE IF NOT EXISTS changes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id     INTEGER NOT NULL,
  path        TEXT NOT NULL,
  change_type TEXT NOT NULL,     -- 'added' | 'removed' | 'modified'
  old_sha256  TEXT,
  new_sha256  TEXT,
  severity    TEXT,              -- 'low' | 'medium' | 'high'
  diff_path   TEXT,              -- optional: path to .diff file
  FOREIGN KEY(scan_id) REFERENCES scans(scan_id)
);
"""

def _is_valid_sqlite_file(p: Path) -> bool:
    if not p.exists():
        return True  # SQLite will create it
    if p.is_dir():
        return False
    try:
        with p.open("rb") as f:
            header = f.read(16)
        return header.startswith(b"SQLite format 3\x00")
    except Exception:
        return False

# Connection + setup helpers

def connect(db_path: Path) -> sqlite3.Connection:
    if db_path.exists() and not _is_valid_sqlite_file(db_path):
        backup = db_path.with_suffix(db_path.suffix + f".corrupt-{int(time.time())}")
        db_path.rename(backup)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con

#    Open (or create) the SQLite file and return a connection. We also set row_factory so we can access columns by name.

def init_db(con: sqlite3.Connection) -> None: # Create tables if they don't exist. Safe to call on every run.
    con.executescript(SCHEMA)
    con.commit()

# Baseline read/write
def write_baseline(con: sqlite3.Connection, files: Dict[str, Dict[str, Any]]) -> None:
    """
    Replace the baseline with the given 'files' mapping. 
    'files' is: { relpath: {"size": int, "sha256": str, "mtime": float, ...}, ... }
    """
    con.execute("DELETE FROM baseline_files")
    rows = [(p, f["size"], f["sha256"], f["mtime"]) for p, f in files.items()]
    con.executemany(
        "INSERT INTO baseline_files (path, size, sha256, mtime) VALUES (?,?,?,?)",
        rows,
    )
    con.commit()

def read_baseline(con: sqlite3.Connection) -> Dict[str, Dict[str, Any]]: # Read baseline rows into a Python dict with the same shape as we write.
    out: Dict[str, Dict[str, Any]] = {}
    for row in con.execute("SELECT path, size, sha256, mtime FROM baseline_files"):
        out[row["path"]] = {
            "size": int(row["size"]),
            "sha256": str(row["sha256"]),
            "mtime": float(row["mtime"]),
        }
    return out

# Scan logging
def start_scan(con: sqlite3.Connection) -> int:
    """
    Insert a new scan row and return the scan_id. We set both started_at and ended_at 
    at creation time; ended_at is updated again when the scan finishes.
    """
    now = datetime.now(UTC).isoformat()
    cur = con.execute(
        "INSERT INTO scans (started_at, ended_at) VALUES (?, ?)",
        (now, now),
    )
    con.commit()
    return int(cur.lastrowid)

def end_scan(con: sqlite3.Connection, scan_id: int) -> None:
    """
    Mark the scan as finished by updating ended_at.
    """
    now = datetime.now(UTC).isoformat()
    con.execute("UPDATE scans SET ended_at = ? WHERE scan_id = ?", (now, scan_id))
    con.commit()

def log_change(
    con: sqlite3.Connection,
    scan_id: int,
    path: str,
    change_type: str,
    old_sha256: str | None,
    new_sha256: str | None,
    severity: str,
    diff_path: str | None,
) -> None:
    """
    Record a single change found during the scan.
    """
    con.execute(
        """
        INSERT INTO changes (scan_id, path, change_type, old_sha256, new_sha256, severity, diff_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (scan_id, path, change_type, old_sha256, new_sha256, severity, diff_path),
    )
    con.commit()