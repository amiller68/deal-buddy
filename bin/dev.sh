#!/bin/bash

# Print current directory
# echo "Current directory: $(pwd)"

# check if db-disk is set as a flag
if [ "$1" == "--db-disk" ]; then
    export DATABASE_PATH=./data/app.db
else
    export DATABASE_PATH=:memory:
fi

# Activate virtual environment
source venv/bin/activate


# Print PYTHONPATH
# echo "PYTHONPATH: $PYTHONPATH"

# Set environment variables
export HOST_NAME=http://localhost:8000
export LISTEN_ADDRESS=localhost
export LISTEN_PORT=8000
export MINIO_ENDPOINT=http://localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin
export DEBUG=True
export LOG_PATH=

# Add the project root to PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$(pwd)"

# Run the server with verbose output
python  ./app/server.py

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
