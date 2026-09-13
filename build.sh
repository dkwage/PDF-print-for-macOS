#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
if [[ ! -d .build-venv ]]; then
  "$PYTHON" -m venv .build-venv
fi
.build-venv/bin/python -m pip install -r requirements-build.txt
bash build_ghostscript.sh
.build-venv/bin/python build_macos_app.py
