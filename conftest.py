"""Conftest: makes the tests/ folder runnable via pytest from the project root.

Usage:
    cd trusted_evidence/
    python -m pytest tests/ -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
