from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any
from typing import Optional
import yaml
import sys
import json

class ConfigError(Exception):
    """Raised when the YAML config is missing or invalid."""
    pass

@dataclass
class SeverityRule:
    pattern: str
    level: str

@dataclass
class Alerts:
    mode: str          # "none" | "webhook"
    webhook_url: str

@dataclass
class Config:
    root: Path
    db_path: Path
    report_dir: Path
    snapshot_dir: Path
    include: List[str]
    exclude: List[str]
    max_diff_bytes: int
    severity: List[SeverityRule]
    alerts: Alerts

    def ensure_dirs(self) -> None: # Create output folders if missing so later code doesn't crash.
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:         # Nice printable view (used by the little self-test below).
        return {
            "root": str(self.root),
            "db_path": str(self.db_path),
            "report_dir": str(self.report_dir),
            "snapshot_dir": str(self.snapshot_dir),
            "include": self.include,
            "exclude": self.exclude,
            "max_diff_bytes": self.max_diff_bytes,
            "severity": [r.__dict__ for r in self.severity],
            "alerts": self.alerts.__dict__,
        }

def load_config(path: Path | str) -> Config: #     # Read YAML, validate fields, build a Config object.
    cfg_path = Path(path).expanduser().resolve()
    if not cfg_path.exists():
        raise ConfigError(f"Config file not found: {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # required: root must be a real existing directory
    root = Path(data.get("root", "")).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ConfigError(f"'root' must be an existing directory: {root}")

    # optional fields with sensible defaults
    db_path = Path(data.get("db_path", "data/fimlite.db"))
    report_dir = Path(data.get("report_dir", "reports"))
    snapshot_dir = Path(data.get("snapshot_dir", "snapshots"))
    include = list(data.get("include", ["**/*"]))
    exclude = list(data.get("exclude", []))
    max_diff_bytes = int(data.get("max_diff_bytes", 200_000))

    # lists of tiny objects
    severity = [
        SeverityRule(pattern=str(r.get("pattern", "**/*")), level=str(r.get("level", "low")))
        for r in data.get("severity", [])
    ]
    alerts_raw = data.get("alerts", {})
    alerts = Alerts(
        mode=str(alerts_raw.get("mode", "none")),
        webhook_url=str(alerts_raw.get("webhook_url", "")),
    )

    cfg = Config(
        root=root,
        db_path=db_path,
        report_dir=report_dir,
        snapshot_dir=snapshot_dir,
        include=include,
        exclude=exclude,
        max_diff_bytes=max_diff_bytes,
        severity=severity,
        alerts=alerts,
    )
    cfg.ensure_dirs()
    return cfg

# ---- tiny self-test so you can run this file directly ----
def _main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python src/fimlite/config.py <path-to-yaml>")
        sys.exit(1)

    try:
        cfg = load_config(argv[0])
    except ConfigError as e:
        print(f"ConfigError: {e}")
        sys.exit(2)

    print("OK")
    print(json.dumps(cfg.to_dict(), indent=2))


def set_root_in_yaml(cfg_path: Path | str, new_root: Path | str) -> Path:
    """
    Update the YAML file's 'root' to the given folder (absolute path).
    Returns the resolved path set.
    """
    cfgp = Path(cfg_path).expanduser().resolve()
    rootp = Path(new_root).expanduser().resolve()
    if not rootp.exists() or not rootp.is_dir():
        raise ConfigError(f"'root' must be an existing directory: {rootp}")

    # load current yaml (or empty), update root, write back
    with cfgp.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data["root"] = str(rootp)

    # keep keys order stable for readability
    with cfgp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)

    return rootp


if __name__ == "__main__":
    _main()
