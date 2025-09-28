# src/fimlite/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List
import yaml


class ConfigError(ValueError):
    """Raised when the YAML config is missing/invalid."""


# Keep this intentionally small/simple for now.
SUPPORTED_HASH_ALG = {"sha256"}

# The keys we allow in the YAML file (helps catch typos).
KNOWN_KEYS = {
    "root",
    "hash_alg",
    "max_file_mb",
    "follow_symlinks",
    "ignore_hidden",
    "include",
    "exclude",
    "severity",
    "alerts",
}


@dataclass
class Config:
    """
    Simple container for validated settings.
    Access fields like cfg.root, cfg.exclude, etc.
    """
    root: Path
    hash_alg: str = "sha256"
    max_file_mb: int = 100
    follow_symlinks: bool = False
    ignore_hidden: bool = True
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=lambda: [
        "**/.git/**",
        "**/node_modules/**",
        "**/*.log",
    ])
    severity: Dict[str, str] = field(default_factory=lambda: {
        "modified": "high",
        "added": "medium",
        "removed": "medium",
    })
    alerts: Dict[str, Any] = field(default_factory=lambda: {"type": "none"})

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        # 1) Required key
        if "root" not in data or not data["root"]:
            raise ConfigError("Missing required config key: 'root'")

        # 2) Unknown keys (helps you catch typos early)
        unknown = set(data.keys()) - KNOWN_KEYS
        if unknown:
            raise ConfigError(f"Unknown config key(s): {', '.join(sorted(unknown))}")

        # 3) Normalize/validate basic types & values
        root = Path(str(data["root"])).expanduser().resolve()
        if not (root.exists() and root.is_dir()):
            raise ConfigError(f"'root' must be an existing directory: {root}")

        hash_alg = str(data.get("hash_alg", "sha256")).lower()
        if hash_alg not in SUPPORTED_HASH_ALG:
            raise ConfigError(f"'hash_alg' must be one of: {sorted(SUPPORTED_HASH_ALG)}")

        try:
            max_file_mb = int(data.get("max_file_mb", 100))
        except Exception as e:
            raise ConfigError("'max_file_mb' must be an integer") from e
        if max_file_mb <= 0:
            raise ConfigError("'max_file_mb' must be > 0")

        follow_symlinks = bool(data.get("follow_symlinks", False))
        ignore_hidden = bool(data.get("ignore_hidden", True))

        include = list(data.get("include", []) or [])
        exclude = list(data.get("exclude", []) or [])

        severity = dict(data.get("severity", {}) or {
            "modified": "high",
            "added": "medium",
            "removed": "medium",
        })

        alerts = dict(data.get("alerts", {}) or {"type": "none"})

        return cls(
            root=root,
            hash_alg=hash_alg,
            max_file_mb=max_file_mb,
            follow_symlinks=follow_symlinks,
            ignore_hidden=ignore_hidden,
            include=include,
            exclude=exclude,
            severity=severity,
            alerts=alerts,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Handy if we need to print or serialize the effective config later."""
        return {
            "root": str(self.root),
            "hash_alg": self.hash_alg,
            "max_file_mb": self.max_file_mb,
            "follow_symlinks": self.follow_symlinks,
            "ignore_hidden": self.ignore_hidden,
            "include": self.include,
            "exclude": self.exclude,
            "severity": self.severity,
            "alerts": self.alerts,
        }


def load_config(path: Path) -> Config:
    """
    Open a YAML file, parse it safely, validate, and return a Config object.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML parse error in {path}: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError("Top-level YAML must be a mapping (key: value)")

    return Config.from_dict(raw)

'''
# --- Self-test runner (optional) ---------------------------------------------
if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Allow: python src/fimlite/config.py configs/example.yml
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("configs/example.yml")
    try:
        cfg = load_config(cfg_path)
    except ConfigError as e:
        print(f"ConfigError: {e}")
        sys.exit(1)

    # Pretty print the effective config
    print("Loaded config:")
    for k, v in cfg.to_dict().items():
        print(f"  {k}: {v}")
'''