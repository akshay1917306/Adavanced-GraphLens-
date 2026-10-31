#!/usr/bin/env bash
# Make a one-time password-reset link (valid 30 minutes) for an account that lost its password and
# its recovery codes. Run from the repository root:  bash scripts/reset-link.sh person@example.com
# The admin key is read from .env and is never printed. Give the link only to that person.
set -uo pipefail
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")/.."
. scripts/lib.sh; load_env

email="${1:-}"
if [ -z "$email" ]; then echo "Usage: bash scripts/reset-link.sh person@example.com"; exit 2; fi
if [ -z "${ADMIN_API_KEY:-}" ]; then
  echo "ADMIN_API_KEY is not set in .env, so the admin routes are switched off."; exit 2
fi

port="${API_PORT:-8000}"
# the key goes in through stdin, so it does not appear in the process list
reply="$(printf 'header = "X-Admin-Key: %s"\n' "$ADMIN_API_KEY" | curl -s -K - -X POST \
  "localhost:$port/api/v1/admin/reset-link" -H 'Content-Type: application/json' \
  -d "$(python -c 'import json,sys;print(json.dumps({"email":sys.argv[1]}))' "$email")")"

url="$(printf '%s' "$reply" | python -c 'import sys,json
try:
    d=json.load(sys.stdin); print(d.get("url",""))
except Exception:
    print("")' 2>/dev/null)"
if [ -z "$url" ]; then
  code="$(printf '%s' "$reply" | python -c 'import sys,json
try:
    print(json.load(sys.stdin)["error"]["code"])
except Exception:
    print("unreadable reply")' 2>/dev/null)"
  echo "No link made ($code)."; exit 1
fi
echo "One-time reset link (works once, expires in 30 minutes):"
echo "$url"
