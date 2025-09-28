from __future__ import annotations
from pathlib import Path
from typing import Optional
import difflib

def baseline_snapshot_path(snapshot_dir: Path, relpath: str) -> Path:
    """
    Where the baseline copy of a file should live:
    <snapshot_dir>/baseline/<relpath>
    """
    return (snapshot_dir / "baseline" / relpath).resolve()

def maybe_write_diff(old_file: Path, new_file: Path, out_path: Path) -> Optional[Path]:
    """
    Make a unified diff between old_file and new_file (text only).
    - Reads both as UTF-8 (ignoring errors).
    - Writes diff to out_path.
    - Returns out_path if there are changes, else None.
    """
    try:
        old_text = old_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        new_text = new_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return None

    diff_lines = difflib.unified_diff(
        old_text, new_text,
        fromfile=str(old_file),
        tofile=str(new_file),
        lineterm=""
    )
    content = "\n".join(diff_lines)
    if not content:
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path
