
#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Add the project root to PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$(pwd)"

echo "running tests"

# if there are additional arguments, pass them to pytest
if [ -n "$@" ]; then
    echo "additional arguments: $@"
    cmd="pytest tests/ -v $@"
    echo $cmd
    $cmd
else
    pytest tests/ -v
fi
