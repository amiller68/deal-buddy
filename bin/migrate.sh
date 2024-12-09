#!/bin/bash

# Enter the virtual environment
source venv/bin/activate

# Parse arguments
DEV=false

while [[ "$#" -gt 0 ]]; do
  case $1 in
  --dev) DEV=true ;;
  *)
    echo "Unknown parameter: $1"
    exit 1
    ;;
  esac
  shift
done

echo "Running migrations..."

# if we're targetting the worker, run the worker
if [ "$DEV" = true ]; then
  DATABASE_PATH="./data/app.db"
fi

# If the DATABASE_PATH environment variable is not set, set a default value
if [ -z "$DATABASE_PATH" ]; then
  # throw an error and exit
  echo "Error: DATABASE_PATH environment variable is not set"
  exit 1
fi

echo "DATABASE_PATH: $DATABASE_PATH"

# Set PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run the migrations
alembic upgrade head

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
