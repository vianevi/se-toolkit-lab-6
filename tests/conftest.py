"""Pytest configuration for agent tests."""

import os
import sys
from pathlib import Path

# Add project root to path so imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set dummy LLM_API_KEY for tests that don't actually call the LLM
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_API_BASE", "http://localhost:8080/v1")
os.environ.setdefault("LLM_MODEL", "test-model")
