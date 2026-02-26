#!/bin/bash

# Ensure the script stops if any command fails
set -e

echo "Starting WIS (Webhook Image Sender)..."

# Check if Python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Error: Python3 is not installed."
    exit
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate and install dependencies
source .venv/bin/activate
echo "Checking dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Launch the application
echo "Launching application..."
python3 main.py &
deactivate