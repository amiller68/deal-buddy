#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status.

# Enter the virtual environment
source venv/bin/activate

# Source environment variables
source .env

# Set default DATABASE_PATH if not set
if [ -z "$DATABASE_PATH" ]; then
    export DATABASE_PATH=./data/app.db
fi
echo "Using DATABASE_PATH: $DATABASE_PATH"

# Get the migration description
DESCRIPTION=$1
if [ -z "$DESCRIPTION" ]; then
    echo "Error: Please provide a description for the migration."
    exit 1
fi
echo "Migration description: $DESCRIPTION"

# Generate alembic migrations
echo "Generating migrations..."
now=$(date +"%Y_%m_%d_%H_%M_%S")
name="${DESCRIPTION}_${now}"

# Run alembic revision and capture output
alembic revision -m "$name"

# Deactivate the virtual environment
deactivate

exit 0
