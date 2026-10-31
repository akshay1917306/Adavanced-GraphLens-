#!/usr/bin/env bash
# Shared helper: read .env, but never override a variable that is already set in the shell.
# (This lets you test against a second stack: COMPOSE_PROJECT_NAME=gltest API_PORT=18000 bash ...)
load_env() {
  local line key
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    case "$line" in ''|\#*) continue ;; esac
    # a line that is not NAME=value (a stray paste, for example) is skipped, never printed
    case "$line" in *=*) ;; *) continue ;; esac
    key="${line%%=*}"
    case "$key" in *[!A-Za-z0-9_]*|[0-9]*) continue ;; esac
    if [ -z "${!key+x}" ]; then export "$key=${line#*=}"; fi
  done < .env
}
