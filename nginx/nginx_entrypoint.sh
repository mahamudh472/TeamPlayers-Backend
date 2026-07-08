#!/bin/sh

# Target directories
LE_DIR="/etc/letsencrypt/live/${DOMAIN_NAME}"
PRIVKEY="${LE_DIR}/privkey.pem"
FULLCHAIN="${LE_DIR}/fullchain.pem"
FLAG_FILE="${LE_DIR}/is_dummy"

if [ ! -f "$PRIVKEY" ] || [ ! -f "$FULLCHAIN" ]; then
    echo "SSL certificates not found for ${DOMAIN_NAME}. Generating self-signed temporary certificates..."
    mkdir -p "${LE_DIR}"
    openssl req -x509 -nodes -days 1 -newkey rsa:2048 \
        -keyout "${PRIVKEY}" \
        -out "${FULLCHAIN}" \
        -subj "/CN=localhost"
    touch "${FLAG_FILE}"
    echo "Self-signed certificate created successfully and flagged."
fi

# Background job to reload nginx config periodically
# This allows pick up of renewed certificates or transition from self-signed to Let's Encrypt
echo "Starting periodic config reloader..."
(
    while :; do
        sleep 6h
        echo "Reloading Nginx config..."
        nginx -s reload
    done
) &

echo "Handing off control to official Nginx entrypoint..."
exec /docker-entrypoint.sh nginx -g "daemon off;"
