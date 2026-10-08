#!/usr/bin/env bash
# One-click setup and run for macOS / Linux
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
