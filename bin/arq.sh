#!/bin/bash

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

arq src.task_manager.worker.WorkerSettings --check

deactivate
