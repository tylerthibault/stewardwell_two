#!/bin/bash
# Entrypoint script for CapRover deployment
# Runs migrations before starting the application

set -e  # Exit on any error

echo "=================================="
echo "CapRover Deployment Starting"
echo "=================================="

# Run database migrations
echo "Running database migrations..."
python migrate_db.py

# Check if migrations succeeded
if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migrations failed!"
    exit 1
fi

echo ""
echo "=================================="
echo "Starting Application Server"
echo "=================================="

# Start the application with Gunicorn
exec gunicorn \
    --bind 0.0.0.0:80 \
    --workers 2 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload \
    --env FLASK_ENV=production \
    run:app
