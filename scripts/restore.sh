#!/usr/bin/env bash
# Restore a backup made by scripts/backup.sh. This REPLACES the current data of Postgres, Neo4j
# and Qdrant, so it asks you to type "restore" first (or pass --yes).
# Run from the repository root:  bash scripts/restore.sh backups/<timestamp> [--yes]
set -euo pipefail
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")/.."
src="${1:-}"
[ -n "$src" ] && [ -d "$src" ] || { echo "Usage: bash scripts/restore.sh backups/<timestamp> [--yes]" >&2; exit 1; }
for f in postgres.dump neo4j.dump qdrant.tar.gz; do
  [ -f "$src/$f" ] || { echo "Missing $src/$f" >&2; exit 1; }
done
[ -f .env ] || { echo "No .env file here. Copy .env.example to .env and fill it in first." >&2; exit 1; }
. scripts/lib.sh; load_env
src_abs="$(cd "$src" && pwd)"

if [ -f "$src/SHA256SUMS" ]; then
  ( cd "$src" && sha256sum -c SHA256SUMS ) || { echo "Checksum mismatch: the backup is damaged." >&2; exit 1; }
fi

if [ "${2:-}" != "--yes" ]; then
  echo "This will replace ALL current data in Postgres, Neo4j and Qdrant with $src."
  read -r -p 'Type "restore" to continue: ' answer
  [ "$answer" = "restore" ] || { echo "Cancelled."; exit 1; }
fi

echo "[0/4] Starting the databases ..."
docker compose up -d postgres qdrant neo4j >/dev/null
docker compose stop web api search >/dev/null 2>&1 || true

echo "[1/4] Postgres ..."
until docker compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do sleep 2; done
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --clean --if-exists --no-owner --exit-on-error < "$src/postgres.dump"

echo "[2/4] Neo4j ..."
docker compose stop neo4j >/dev/null
docker compose run --rm --no-deps -v "$src_abs:/backup" --entrypoint bash neo4j -c \
  "neo4j-admin database load neo4j --from-path=/backup --overwrite-destination=true"

echo "[3/4] Qdrant ..."
docker compose stop qdrant >/dev/null
docker compose run --rm --no-deps -v "$src_abs:/backup" --entrypoint sh qdrant -c \
  "rm -rf /qdrant/storage/* /qdrant/storage/.[!.]* 2>/dev/null; cd /qdrant/storage && tar xzf /backup/qdrant.tar.gz"

echo "[4/4] Starting everything ..."
docker compose up -d >/dev/null
echo "Restored. Wait about a minute, then run: bash scripts/check.sh"
