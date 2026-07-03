#!/bin/sh
set -e

# The mounted volume (see docker-compose.yml) may be empty on first run —
# alembic upgrade head creates the SQLite file and all tables via the
# migration chain, same as local setup (README → Database migrations).
alembic upgrade head
exec uvicorn main:app --host 0.0.0.0 --port 8000
