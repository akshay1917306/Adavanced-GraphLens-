#!/usr/bin/env bash
# Print the size of each data store and ask the running app one saved question.
# Run from the repository root:  bash scripts/check.sh
set -uo pipefail
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")/.."
. scripts/lib.sh; load_env
fail=0

pg() { docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "$1" 2>/dev/null; }
echo "Postgres text units : $(pg 'select count(*) from text_units')"
echo "Postgres documents  : $(pg 'select count(*) from documents')"
echo "Postgres extractions  : $(pg 'select count(*) from extraction_cache')"

cy() { docker compose exec -T neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" --format plain "$1" 2>/dev/null | tail -n 1; }
echo "Neo4j entities      : $(cy 'MATCH (e:Entity) RETURN count(e)')"
echo "Neo4j communities   : $(cy 'MATCH (c:Community) RETURN count(c)')"

alias_target="$(curl -s localhost:${QDRANT_PORT:-6333}/aliases | python -c 'import sys,json;print([a["collection_name"] for a in json.load(sys.stdin)["result"]["aliases"]])' 2>/dev/null)"
echo "Qdrant aliases      : $alias_target"

port="${API_PORT:-8000}"
echo "API health          : $(curl -s -o /dev/null -w '%{http_code}' localhost:$port/api/v1/health)"
tok="$(curl -s -X POST -H 'Content-Type: application/json' -d '{}' localhost:$port/api/v1/visitor | python -c 'import sys,json;print(json.load(sys.stdin).get("token",""))' 2>/dev/null)"
q="$(curl -s localhost:$port/api/v1/examples | python -c 'import sys,json;d=json.load(sys.stdin);print(d["questions"][0])' 2>/dev/null)"
if [ -n "$tok" ] && [ -n "$q" ]; then
  code="$(curl -s -o /tmp/gl_check.json -w '%{http_code}' -X POST localhost:$port/api/v1/ask \
    -H 'Content-Type: application/json' -H "X-Visitor-Token: $tok" -d "{\"question\": \"$q\"}")"
  echo "Saved question      : HTTP $code"
  [ "$code" = "200" ] || fail=1
else
  echo "Saved question      : could not get a visitor token or example (see runbook)"; fail=1
fi
[ "$fail" = 0 ] && echo "CHECK OK" || { echo "CHECK FAILED"; exit 1; }
