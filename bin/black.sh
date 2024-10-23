#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Add the project root to PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$(pwd)"

# Run the server with verbose output
python -m black .

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
