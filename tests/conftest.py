"""pytest configuration"""

import pytest
import sys
from pathlib import Path

# Add python package to path
python_path = Path(__file__).parent.parent / "python"
sys.path.insert(0, str(python_path))
