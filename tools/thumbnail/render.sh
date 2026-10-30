#!/usr/bin/env bash
# Wrapper: always uses the shared venv. Example:
#   tools/thumbnail/render.sh -t B --base frame.jpg --headline "Show up anyway." --accent anyway --label "Discipline" --out out.jpg
DIR="$(cd "$(dirname "$0")" && pwd)"
export U2NET_HOME="$DIR/models"
exec "$DIR/.venv/bin/python" "$DIR/render.py" "$@"
