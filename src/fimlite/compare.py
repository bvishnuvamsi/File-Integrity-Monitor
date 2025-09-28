from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import fnmatch

@dataclass
class Change:
    path: str
    change_type: str     # 'added' | 'removed' | 'modified'
    old_sha256: str | None
    new_sha256: str | None
    severity: str        # 'low' | 'medium' | 'high'
    diff_path: str | None = None  # will be filled later by diffing code

def _severity_for(path: str, rules: List[dict]) -> str:
    """
    Pick the first rule whose glob pattern matches the relative path.
    If nothing matches, default to 'low'.
    """
    for r in rules:
        pat = r.get("pattern", "**/*")
        lvl = r.get("level", "low")
        if fnmatch.fnmatch(path, pat):
            return str(lvl)
    return "low"

def compare(
    baseline: Dict[str, dict],
    current: Dict[str, dict],
    severity_rules: List[dict],
) -> List[Change]:
    """
    Compare baseline vs current and return a list of Change objects.
    - baseline/current: { relpath: {"size": int, "sha256": str, "mtime": float, ...}, ... }
    - severity_rules:   [ {"pattern": "...", "level": "..."}, ... ]
    """
    changes: List[Change] = []

    base_paths = set(baseline.keys())
    curr_paths = set(current.keys())

    # Added: now but not before
    for p in sorted(curr_paths - base_paths):
        changes.append(Change(
            path=p, change_type="added",
            old_sha256=None,
            new_sha256=current[p]["sha256"],
            severity=_severity_for(p, severity_rules),
        ))

    # Removed: before but not now
    for p in sorted(base_paths - curr_paths):
        changes.append(Change(
            path=p, change_type="removed",
            old_sha256=baseline[p]["sha256"],
            new_sha256=None,
            severity=_severity_for(p, severity_rules),
        ))

    # Modified: in both, but sha changed
    for p in sorted(base_paths & curr_paths):
        if baseline[p]["sha256"] != current[p]["sha256"]:
            changes.append(Change(
                path=p, change_type="modified",
                old_sha256=baseline[p]["sha256"],
                new_sha256=current[p]["sha256"],
                severity=_severity_for(p, severity_rules),
            ))

    return changes