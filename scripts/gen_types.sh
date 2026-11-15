#!/usr/bin/env bash
# Regenerates frontend/lib/api-types.gen.ts from the pydantic models (via the OpenAPI schema).
# Run after any change to backend/trend_detective/models.py or backend/api/schemas.py.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMA="$ROOT/docs/openapi.json"

cd "$ROOT/backend"
.venv/bin/python -c "
import json
from api.main import app
print(json.dumps(app.openapi(), indent=1))
" > "$SCHEMA"

cd "$ROOT/frontend"
npx --no-install openapi-typescript "$SCHEMA" -o lib/api-types.gen.ts
