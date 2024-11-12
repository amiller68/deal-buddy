#!/bin/bash

# Parse arguments
DB_DISK=true
WORKER=true

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --db-disk) DB_DISK=true ;;
        --worker) WORKER=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Set database path
if [ "$DB_DISK" = true ]; then
    export DATABASE_PATH=./data/app.db
else
    export DATABASE_PATH=:memory:
fi

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

# Add the project root to PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$(pwd)"

# Function to cleanup processes on exit
cleanup() {
    echo "Shutting down processes..."
    kill $APP_PID 2>/dev/null
    if [ "$WORKER" = true ]; then
        kill $WORKER_PID 2>/dev/null
    fi
    deactivate
    exit 0
}

trap cleanup EXIT INT TERM

# Run the FastAPI server in the background
python -m src &
APP_PID=$!

# Run the ARQ worker if requested
if [ "$WORKER" = true ]; then
    echo "Starting ARQ worker..."
    arq src.task_manager.worker.WorkerSettings --watch src/task_manager &
    WORKER_PID=$!
    wait $APP_PID $WORKER_PID
else
    wait $APP_PID
fi