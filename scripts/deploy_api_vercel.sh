#!/usr/bin/env bash
# Deploys the FastAPI back-end to Vercel as a Python function, from the committed state (HEAD),
# never from uncommitted changes. Staging folder: .deploy/api (ignored by git).
# Usage: scripts/deploy_api_vercel.sh [--prod]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$ROOT/.deploy/api"
PROJECT="trend-detective-api"

mkdir -p "$STAGE"
# Empty the folder, except the link to the Vercel project (.vercel).
find "$STAGE" -mindepth 1 -maxdepth 1 ! -name .vercel -exec rm -rf {} +

cd "$ROOT"
git archive --format=tar HEAD backend/api backend/trend_detective backend/requirements.txt \
  | tar -x -C "$STAGE" --strip-components=1
find "$STAGE" -name "__pycache__" -type d -prune -exec rm -rf {} +

DEPS=$(grep -vE '^\s*(#|$)' "$STAGE/requirements.txt" | sed 's/.*/  "&",/')
cat > "$STAGE/pyproject.toml" <<EOF
[project]
name = "trend-detective-api"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
$DEPS
]

[tool.vercel]
entrypoint = "api.main:app"
EOF
echo "3.12" > "$STAGE/.python-version"
cat > "$STAGE/vercel.json" <<'EOF'
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": { "api/main.py": { "maxDuration": 60 } }
}
EOF

cd "$STAGE"
[ -d .vercel ] || vercel link --yes --project "$PROJECT" >/dev/null
vercel deploy --yes "$@"
