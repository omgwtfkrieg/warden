#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Running seed..."
python -m app.seed

echo "Starting warden-api..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8484
