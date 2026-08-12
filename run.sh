#!/bin/sh

set -e

export DB_PASSWORD="$(openssl rand -hex 24)"
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
export SSH_PIVOT_PASSWORD="$(openssl rand -hex 24)"

docker compose down -v
docker compose up "$@"