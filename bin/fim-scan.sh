#!/usr/bin/env bash
set -euo pipefail

# Resolve project root from this script's location
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$PROJECT/configs/example.yml"
LOG="$PROJECT/scan.log"

# Activate a venv if available (fvenv or .venv), otherwise continue with system python
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  : # already in a venv
elif [[ -f "$PROJECT/fvenv/bin/activate" ]]; then
  source "$PROJECT/fvenv/bin/activate"
elif [[ -f "$PROJECT/.venv/bin/activate" ]]; then
  source "$PROJECT/.venv/bin/activate"
else
  echo "[$(date -u +%FT%TZ)] WARN: no venv found, using system python: $(command -v python3)" >> "$LOG"
fi

cd "$PROJECT"

echo "[$(date -u +%FT%TZ)] scan start" >> "$LOG"
# Run the scan (PYTHONPATH=src because you’re using a src/ layout)
if PYTHONPATH=src python3 -m fimlite.cli scan --config "$CONFIG" >> "$LOG" 2>&1; then
  echo "[$(date -u +%FT%TZ)] scan end (ok)" >> "$LOG"
else
  echo "[$(date -u +%FT%TZ)] scan end (FAILED)" >> "$LOG"
fi

