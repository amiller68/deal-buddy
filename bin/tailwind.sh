#!/bin/bash

source venv/bin/activate

# Check if -w flag is set
# If it is, start the watcher
if [ "$1" == "-w" ]; then
	npx tailwindcss -i styles/main.css -o static/css/main.css --watch
else
	npx tailwindcss -i styles/main.css -o static/css/main.css
fi

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
