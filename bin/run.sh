#!/bin/bash

WORKER=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --worker) WORKER=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

source venv/bin/activate

export LISTEN_ADDRESS=0.0.0.0
export LISTEN_PORT=8000

export DEBUG=False

if [ "$WORKER" = true ]; then
    arq src.task_manager.worker.WorkerSettings
else
    python -m src
fi

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
