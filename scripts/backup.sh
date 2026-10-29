#!/usr/bin/env bash
# Back up the three data stores of GraphLens into backups/<timestamp>/.
#   Postgres : pg_dump (custom format), taken while the database runs.
#   Neo4j    : neo4j-admin dump. Community Edition can only dump a stopped database,
#              so Neo4j (and with it the API and search) is stopped for about a minute.
#   Qdrant   : the storage volume as a tar archive, taken while Qdrant is stopped
#              (this keeps collections and the live alias together).
# Redis is not backed up: it only holds rate-limit and daily-cost counters.
# Run from the repository root:  bash scripts/backup.sh [target-dir]
set -euo pipefail
export MSYS_NO_PATHCONV=1   # Git Bash on Windows: do not rewrite container paths

cd "$(dirname "$0")/.."
[ -f .env ] || { echo "No .env file here. Run this from the repository root." >&2; exit 1; }
. scripts/lib.sh; load_env

stamp="$(date +%Y%m%d-%H%M%S)"
dest="${1:-backups/$stamp}"
mkdir -p "$dest"
dest_abs="$(cd "$dest" && pwd)"
echo "Backup folder: $dest_abs"

echo "[1/3] Postgres ..."
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$dest/postgres.dump"

echo "[2/3] Neo4j (stops Neo4j, API, web and search for a short time) ..."
docker compose stop web api search neo4j >/dev/null 2>&1 || docker compose stop web api neo4j >/dev/null
docker compose run --rm --no-deps -v "$dest_abs:/backup" --entrypoint bash neo4j -c \
  "neo4j-admin database dump neo4j --to-path=/backup --overwrite-destination=true"

echo "[3/3] Qdrant (stops Qdrant for a few seconds) ..."
docker compose stop qdrant >/dev/null
docker compose run --rm --no-deps -v "$dest_abs:/backup" --entrypoint sh qdrant -c \
  "cd /qdrant/storage && tar czf /backup/qdrant.tar.gz ."

echo "Starting the stack again ..."
docker compose up -d >/dev/null

( cd "$dest" && sha256sum postgres.dump neo4j.dump qdrant.tar.gz > SHA256SUMS )
echo "Done. Files:"
ls -l "$dest"
