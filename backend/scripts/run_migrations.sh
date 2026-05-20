#!/usr/bin/env bash
set -euo pipefail

if [[ -f /etc/supfile/supfile.env ]]; then
  set -a
  # shellcheck source=/dev/null
  source /etc/supfile/supfile.env
  set +a
fi

echo "[SUPFile] Running Alembic migrations on ${DATABASE_URL:-undefined}"
if [[ -x /opt/supfile/venv/bin/python ]]; then
  /opt/supfile/venv/bin/python -m alembic upgrade head
else
  python -m alembic upgrade head
fi
echo "[SUPFile] Migrations complete"
