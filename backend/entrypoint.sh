#!/bin/sh
set -e

echo "==> Running database migrations (alembic upgrade head)..."
alembic upgrade head

echo "==> Starting Supervisord (Backend API + Taskiq Worker + Taskiq Scheduler)..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf -n
