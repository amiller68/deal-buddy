#!/bin/bash

# Parse arguments
WORKER=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --worker) WORKER=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export HOST_NAME=http://localhost:8000
export LISTEN_ADDRESS=localhost
export LISTEN_PORT=8000
export MINIO_ENDPOINT=http://localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin
export DEBUG=True
export DEV_MODE=True
export LOG_PATH=
export REDIS_URL=redis://localhost:6379
export DATABASE_PATH=./data/app.db

# if the database path doesn't exist, create it
if [ ! -f "$DATABASE_PATH" ]; then
    ./bin/migrate.sh
fi

# Add the project root to PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$(pwd)"

# if we're targetting the worker, run the worker
if [ "$WORKER" = true ]; then
    arq src.task_manager.worker.WorkerSettings --watch ./src --verbose
else
    # Run the FastAPI server in the background
    python -m src
fi

# Deactivate virtual environment
deactivate