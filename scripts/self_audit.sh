#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m unittest discover -s tests -v
python3 -m compileall -q pragmatic_audit
python3 scripts/capture_terminal.py
python3 -m pragmatic_audit . --ci --fail-on high --format markdown --output examples/self-audit.md
echo "Wrote examples/self-audit.md"
