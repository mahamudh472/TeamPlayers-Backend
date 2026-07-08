#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Wait for database using Python sockets
python -c "
import socket
import time
import os

host = os.environ.get('POSTGRES_HOST', 'db')
port = int(os.environ.get('POSTGRES_PORT', 5432))

print(f'Waiting for PostgreSQL at {host}:{port}...')
while True:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect((host, port))
            break
    except (socket.error, ConnectionRefusedError):
        time.sleep(0.5)
print('PostgreSQL is up and running!')
"

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Daphne server
echo "Starting server..."
exec daphne -b 0.0.0.0 -p 8000 TeamPlayers.asgi:application
