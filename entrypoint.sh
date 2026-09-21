#!/bin/sh
set -e

# Shared bootstrap for every container built from this image (django,
# celery-worker, celery-beat - see docker-compose.yaml) - each just
# overrides `command:`, which becomes "$@" below. Key generation and the DB
# wait are idempotent/harmless to repeat per-container.

mkdir -p secrets

if [ ! -f secrets/store_admin_private_key.pem ]; then
    echo "Generating store-admin RSA key pair..."
    openssl genpkey -algorithm RSA -out secrets/store_admin_private_key.pem -pkeyopt rsa_keygen_bits:4096
    openssl rsa -pubout -in secrets/store_admin_private_key.pem -out secrets/store_admin_public_key.pem
fi

if [ ! -f secrets/buyer_private_key.pem ]; then
    echo "Generating buyer RSA key pair..."
    openssl genpkey -algorithm RSA -out secrets/buyer_private_key.pem -pkeyopt rsa_keygen_bits:4096
    openssl rsa -pubout -in secrets/buyer_private_key.pem -out secrets/buyer_public_key.pem
fi

echo "Waiting for database ($DB_HOST:$DB_PORT)"
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; do
    sleep 1
done

# Migrations only run once, from the container that's actually starting the
# web server - running them from every celery container too would race.
if [ "$1" = "gunicorn" ]; then
    echo "Applying migrations"
    uv run python manage.py migrate --noinput
fi

echo "Starting: $*"
exec uv run "$@"
