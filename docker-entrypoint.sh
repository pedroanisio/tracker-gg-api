#!/bin/bash
set -e

# Docker entrypoint script for Tracker.gg Valorant API

echo "🚀 Starting Tracker.gg Valorant API..."

# Function to wait for database
wait_for_db() {
    echo "⏳ Waiting for database connection..."
    while ! pg_isready -h postgres -p 5432 -U ${POSTGRES_USER:-valorant_user} -d ${POSTGRES_DB:-valorant_tracker} >/dev/null 2>&1; do
        sleep 1
    done
    echo "✅ Database is ready!"
}

# Function to initialize database
init_db() {
    echo "🔧 Initializing database..."
    python -m src ingest --init-db
    echo "✅ Database initialized!"
}

# Function to load data
load_data() {
    echo "📥 Loading data from /app/data directory..."
    if [ -d "/app/data" ] && [ "$(ls -A /app/data/*.json 2>/dev/null)" ]; then
        python -m src ingest --load-directory /app/data
        echo "✅ Data loaded!"
    else
        echo "ℹ️ No data files found in /app/data directory"
    fi
}

# Function to start API server
start_api() {
    echo "🌐 Starting API server..."
    python -m src api --host 0.0.0.0 --port 8000
}

# Function to run ingestion command
run_ingestion() {
    echo "🔄 Running ingestion command: $@"
    python -m src ingest "$@"
}

# Main logic
case "${1:-api}" in
    "api")
        wait_for_db
        init_db
        load_data
        start_api
        ;;
    "init-db")
        wait_for_db
        init_db
        ;;
    "load-data")
        wait_for_db
        load_data
        ;;
    "ingest")
        wait_for_db
        shift
        run_ingestion "$@"
        ;;
    "full-setup")
        wait_for_db
        init_db
        load_data
        echo "🎉 Full setup complete!"
        ;;
    *)
        echo "🤖 Running custom command: $@"
        exec "$@"
        ;;
esac 