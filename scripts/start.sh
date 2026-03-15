#!/usr/bin/env bash
set -e

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt
python -m flask --app app run --host=127.0.0.1 --port="${PORT:-8000}"
