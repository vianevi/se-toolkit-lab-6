"""Pytest configuration for agent tests."""

import os
import sys
from pathlib import Path

# Add project root to path so imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env files first
# This ensures tests use real LLM credentials if available
from dotenv import load_dotenv
load_dotenv(project_root / ".env.agent.secret")
load_dotenv(project_root / ".env.docker.secret")

# Only set dummy values if real credentials are not configured
# This allows tests to run with real LLM when credentials exist
if not os.getenv("LLM_API_KEY"):
    os.environ["LLM_API_KEY"] = "test-key"
if not os.getenv("LLM_API_BASE"):
    os.environ["LLM_API_BASE"] = "http://localhost:8080/v1"
if not os.getenv("LLM_MODEL"):
    os.environ["LLM_MODEL"] = "test-model"
