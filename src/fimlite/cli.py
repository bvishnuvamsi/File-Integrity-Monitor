from __future__ import annotations
import argparse
import json
from pathlib import Path

from fimlite.config import load_config, ConfigError
from fimlite import db as dbmod
from fimlite.walker import iter_files, is_text_file
from fimlite.compare import compare
from fimlite.diffing import baseline_snapshot_path, maybe_write_diff
from fimlite.report import render_report

import os
import json 

from fimlite.config import set_root_in_yaml  # add to the imports

def cmd_select_root(config_path: Path, direct_path: Path | None) -> int:
    """
    Ask user to pick a folder (GUI or prompt) and save it to YAML 'root'.
    """
    # 1) pick the folder
    if direct_path is not None:
        chosen = direct_path.expanduser().resolve()
    else:
        chosen = _select_folder_gui()
        if chosen is None:
            # fallback to prompt
            p = input("Enter absolute path to the folder to monitor (or leave blank to cancel): ").strip()
            if not p:
                print("Cancelled.")
                return 4
            chosen = Path(p).expanduser().resolve()

    if not chosen.exists() or not chosen.is_dir():
        print(f"Not a directory: {chosen}")
        return 5

    # 2) save into YAML and re-load to confirm
    try:
        set_root_in_yaml(config_path, chosen)
        cfg = load_config(config_path)
    except ConfigError as e:
        print(f"ConfigError: {e}")
        return 2

    print(json.dumps({
        "ok": True,
        "root_set": str(cfg.root),
        "config": str(config_path.resolve())
    }, indent=2))
    return 0


def cmd_baseline(config_path: Path) -> int:
    """Create/refresh the baseline and save small text snapshots."""
    try:
        cfg = load_config(config_path)
    except ConfigError as e:
        print(f"ConfigError: {e}")
        return 2

    # Build current files map
    files_map: dict[str, dict] = {}
    for info in iter_files(cfg.root, cfg.include, cfg.exclude):
        files_map[info.relpath] = {
            "size": info.size,
            "sha256": info.sha256,
            "mtime": info.mtime,
            "abs": str(info.abs_path),
        }

    # Write baseline to SQLite
    con = dbmod.connect(cfg.db_path)
    dbmod.init_db(con)
    dbmod.write_baseline(con, files_map)

    # Save small text snapshots for diffing later
    snap_base = cfg.snapshot_dir / "baseline"
    saved = 0
    for rel, meta in files_map.items():
        src = Path(meta["abs"])
        # keep it light: only snapshot small text files
        if meta["size"] <= cfg.max_diff_bytes and is_text_file(src):
            dst = snap_base / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                # copy contents preserving timestamps/metadata where possible
                dst.write_bytes(src.read_bytes())
                saved += 1
            except Exception:
                pass

    print(json.dumps({
        "ok": True,
        "baseline_files": len(files_map),
        "snapshots_saved": saved,
        "db": str(cfg.db_path),
        "snapshot_dir": str(snap_base),
    }, indent=2))
    return 0

def cmd_scan(config_path: Path) -> int:
    """Compare current state with baseline, log changes, and write HTML report."""
    try:
        cfg = load_config(config_path)
    except ConfigError as e:
        print(f"ConfigError: {e}")
        return 2

    con = dbmod.connect(cfg.db_path)
    dbmod.init_db(con)

    baseline_map = dbmod.read_baseline(con)
    if not baseline_map:
        print("No baseline found. Run: baseline --config <path-to-yaml>")
        return 3

    # Build current map
    current_map: dict[str, dict] = {}
    for info in iter_files(cfg.root, cfg.include, cfg.exclude):
        current_map[info.relpath] = {
            "size": info.size,
            "sha256": info.sha256,
            "mtime": info.mtime,
            "abs": str(info.abs_path),
        }

    scan_id = dbmod.start_scan(con)

    # Compute changes with severities
    changes = compare(
        baseline_map, current_map,
        [{"pattern": r.pattern, "level": r.level} for r in cfg.severity]
    )

    # For modified files, try to write diffs using baseline snapshots
    diffs_root = cfg.report_dir / "diffs" / str(scan_id)
    made_diffs = 0
    for ch in changes:
        diff_path_str = None
        if ch.change_type == "modified":
            old_file = baseline_snapshot_path(cfg.snapshot_dir, ch.path)
            new_file = Path(current_map[ch.path]["abs"]).resolve()
            try:
                size_ok = new_file.stat().st_size <= cfg.max_diff_bytes
            except Exception:
                size_ok = False
            if old_file.exists() and new_file.exists() and size_ok:
                out_path = diffs_root / (ch.path + ".diff")
                res = maybe_write_diff(old_file, new_file, out_path)
                if res is not None:
                    diff_path_str = str(res)
                    made_diffs += 1

        dbmod.log_change(con, scan_id, ch.path, ch.change_type,
                         ch.old_sha256, ch.new_sha256, ch.severity, diff_path_str)

    dbmod.end_scan(con, scan_id)

    # Counts for summary + report
    counts = {
        "total": len(changes),
        "added": sum(1 for c in changes if c.change_type == "added"),
        "removed": sum(1 for c in changes if c.change_type == "removed"),
        "modified": sum(1 for c in changes if c.change_type == "modified"),
        "diffs": made_diffs,
    }

    # Get timestamps for the header
    row = next(iter(con.execute(
        "SELECT started_at, ended_at FROM scans WHERE scan_id = ?", (scan_id,)
    )), None)
    started_at = row["started_at"] if row else ""
    ended_at   = row["ended_at"] if row else ""

    # Render HTML
    out_html = cfg.report_dir / f"scan-{scan_id}.html"
    render_report(out_html, scan_id, started_at, ended_at,
                  [c.__dict__ for c in changes], counts)

    print(json.dumps({
        "ok": True,
        "scan_id": scan_id,
        **counts,
        "report": str(out_html),
    }, indent=2))
    return 0

def _select_folder_gui(initial: Path | None = None) -> Path | None:
    """
    Try to open a native folder chooser using tkinter.
    Returns Path or None if cancelled/unavailable.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        chosen = filedialog.askdirectory(
            initialdir=str(initial) if initial else os.path.expanduser("~"),
            title="Select folder to monitor"
        )
        root.destroy()
        if chosen:
            return Path(chosen).expanduser().resolve()
        return None
    except Exception:
        return None
    
def main():
    parser = argparse.ArgumentParser(
        prog="fimlite",
        description="FIMLite — simple file integrity monitor"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_base = sub.add_parser("baseline", help="Create/refresh the baseline")
    p_base.add_argument("--config", type=Path, required=True, help="Path to YAML config")

    p_scan = sub.add_parser("scan", help="Compare current state vs baseline and write report")
    p_scan.add_argument("--config", type=Path, required=True, help="Path to YAML config")

    p_sel = sub.add_parser("select-root", help="Choose the folder to monitor and save it to the config")
    p_sel.add_argument("--config", type=Path, required=True, help="Path to YAML config")
    p_sel.add_argument("--path", type=Path, help="Set folder directly (skip dialog)")

    args = parser.parse_args()

    if args.command == "baseline":
        raise SystemExit(cmd_baseline(args.config))
    elif args.command == "scan":
        raise SystemExit(cmd_scan(args.config))
    elif args.command == "select-root":
        raise SystemExit(cmd_select_root(args.config, args.path))


if __name__ == "__main__":
    main()
