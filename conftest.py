"""Pytest configuration and fixtures.

This file sets up the Python path so tests can import from the backend package.
"""

import sys
from pathlib import Path

# Add backend directory to Python path for imports
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))
