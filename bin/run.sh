#!/bin/bash

source venv/bin/activate

export LISTEN_ADDRESS=0.0.0.0
export LISTEN_PORT=8000

export DEBUG=False
python -m app

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
