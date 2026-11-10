#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PORT="${PORT:-8787}"
IMAGE="lang-research-$(basename "$ROOT" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-')"

docker build --tag "$IMAGE" "$ROOT"

CID="$(docker run --detach --rm \
  --user "$(id -u):$(id -g)" \
  --publish "127.0.0.1:${PORT}:8000" \
  --volume "$ROOT:/course:ro" \
  "$IMAGE")"

cleanup() {
  docker stop "$CID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

URL="http://127.0.0.1:${PORT}/app/index.html"
sleep 1

case "$(uname -s)" in
  Darwin) open "$URL" >/dev/null 2>&1 || true ;;
  Linux) xdg-open "$URL" >/dev/null 2>&1 || true ;;
esac

printf '\nCourse is running at %s\n' "$URL"
printf 'Progress is kept in your browser; use Export progress to keep a copy.\n'
printf 'Press Ctrl-C to stop the course.\n\n'
docker logs --follow "$CID"
