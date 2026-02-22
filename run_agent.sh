#!/bin/bash
# Convenient wrapper to run the Qiskit SWE Agent

# Ensure we're in the project root
cd "$(dirname "$0")"

# Activate virtual environment if present
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the agent via main.py (which handles sys.path)
python main.py "$@"
