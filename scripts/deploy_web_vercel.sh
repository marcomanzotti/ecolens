#!/usr/bin/env bash
# Deploys the Next.js front-end to Vercel from the committed state (HEAD), never from
# uncommitted changes. Staging folder: .deploy/web (ignored by git).
# Usage: API_URL=https://... scripts/deploy_web_vercel.sh [--prod]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$ROOT/.deploy/web"
PROJECT="trend-detective"
API_URL="${API_URL:?set API_URL to the public back-end URL}"

mkdir -p "$STAGE"
find "$STAGE" -mindepth 1 -maxdepth 1 ! -name .vercel -exec rm -rf {} +

cd "$ROOT"
git archive --format=tar HEAD frontend | tar -x -C "$STAGE" --strip-components=1

cd "$STAGE"
[ -d .vercel ] || vercel link --yes --project "$PROJECT" >/dev/null
vercel deploy --yes --build-env NEXT_PUBLIC_API_URL="$API_URL" --env NEXT_PUBLIC_API_URL="$API_URL" "$@"
