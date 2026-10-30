#!/usr/bin/env bash
# Install the existing renderer locally; all runtime paths are configurable.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON=python3
OUTPUT_DIR="$DIR/../../.local/thumbnail/covers"
WITH_MASK=no
while [[ $# -gt 0 ]]; do
  case "$1" in
    --python) PYTHON="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --with-mask) WITH_MASK=yes; shift ;;
    *) echo "Usage: setup.sh [--python PATH] [--output-dir DIR] [--with-mask]" >&2; exit 2 ;;
  esac
done
# Resolve caller-relative output before changing directory.
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
cd "$DIR"
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install --quiet -r requirements.txt
if [[ "$WITH_MASK" == yes ]]; then
  .venv/bin/python -m pip install --quiet -r requirements-mask.txt
fi
mkdir -p models
chmod +x render.sh
bash render.sh -t C --headline "A useful next step" --label "Project notes" --out "$OUTPUT_DIR/setup_test_C.jpg"
echo "OK — renderer ready; smoke test: $OUTPUT_DIR/setup_test_C.jpg"
