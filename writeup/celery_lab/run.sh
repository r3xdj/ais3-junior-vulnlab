#!/bin/sh
set -e

redis-server --daemonize yes

echo "Redis started."
echo "Celery worker is NOT started."

exec bash