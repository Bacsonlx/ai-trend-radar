#!/bin/zsh
set -eu

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$PROJECT_DIR/logs"
cd "$PROJECT_DIR"

exec /Users/linxin/miniconda3/bin/python "$PROJECT_DIR/main.py"
