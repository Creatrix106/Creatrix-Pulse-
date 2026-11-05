#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "Initializing database & seeding demo datasets..."
python3 -m app.db.seed

echo "Starting Creatrix Pulse Backend API on http://0.0.0.0:8000..."
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
