"""
Convenience entry point — run the SWE-agent from the project root:

    python main.py --repo Qiskit/qiskit --issue 12345
"""

import os
import sys

# Add this directory to sys.path so all packages resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.cli import main

if __name__ == "__main__":
    main()
