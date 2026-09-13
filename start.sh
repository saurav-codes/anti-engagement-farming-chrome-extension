#!/usr/bin/env bash

# Local dev server for the engagement-farming classifier.
# Creates .venv, installs deps (uses uv when available),
# downloads the model from Hugging Face on first start,
# then serves on http://127.0.0.1:8000

set -euo pipefail
cd "$(dirname "$0")"
if command -v uv >/dev/null 2>&1; then
  [ -d .venv ] || uv venv .venv
  uv pip install --python .venv/bin/python -r requirements.txt
else
  [ -d .venv ] || python3 -m venv .venv
  .venv/bin/pip install --quiet -r requirements.txt
fi
exec .venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000
