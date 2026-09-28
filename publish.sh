#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
KEY="${AESN_PUBLISHER_KEY:-$HOME/.config/aesn/publisher.json}"
rm -rf dist build
python3 -m build >/dev/null
PYTHONPATH="$HOME/tmig/src" python3 -m tmig_bridge.gate --repo "$(pwd)" --key "$KEY" || exit 1
TOKEN="$(vault get pypi 2>/dev/null || true)"
[ -z "$TOKEN" ] && exit 67
TWINE_USERNAME=__token__ TWINE_PASSWORD="$TOKEN" twine upload --non-interactive dist/*
