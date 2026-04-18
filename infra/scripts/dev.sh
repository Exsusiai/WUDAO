#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

# Check .env
if [ ! -f .env ]; then
  echo "⚠️  No .env file found. Copying from .env.example..."
  cp .env.example .env
  echo "   Created .env — please review and update before production use."
fi

# Ensure Python venv
if [ ! -d .venv ]; then
  echo "📦 Creating Python virtual environment..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e ".[dev]" --quiet
else
  source .venv/bin/activate
fi

# Ensure DB
if [ ! -f data/wudao.db ]; then
  echo "🗄️  Initializing database..."
  mkdir -p data
  alembic -c alembic.ini upgrade head
  python infra/db/seed.py
fi

# Ensure frontend deps
if [ ! -d apps/web/node_modules ]; then
  echo "📦 Installing frontend dependencies..."
  (cd apps/web && npm install --silent)
fi

echo ""
echo "🚀 Starting Wudao dev environment..."
echo "   API:      http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   Mode:     $(python -c 'import os; print(os.getenv("APP_MODE", "sandbox"))')"
echo ""

# Start API + Frontend in parallel
trap 'kill 0' EXIT

uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload &
(cd apps/web && npm run dev) &

wait
