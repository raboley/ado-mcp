"""
Global pytest configuration and fixtures.

This file ensures that .env variables are loaded before any tests run,
regardless of how the tests are executed (pytest, IDE, etc.).
"""

import os
from pathlib import Path

from dotenv import load_dotenv


def pytest_configure():
    """
    Configure pytest and load environment variables.
    
    This runs before any tests are collected or executed, ensuring
    that .env variables are available in all test environments.
    """
    # Find the project root (where .env should be located)
    project_root = Path(__file__).parent
    env_file = project_root / ".env"
    
    if env_file.exists():
        # Load .env file, overriding any existing environment variables
        load_dotenv(env_file, override=True)
        print(f"✓ Loaded environment variables from {env_file}")
    else:
        print(f"⚠️  No .env file found at {env_file}")
    
    # Verify critical variables are set
    required_vars = ["AZURE_DEVOPS_EXT_PAT", "ADO_ORGANIZATION_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing required environment variables: {missing_vars}")
        print("   Some tests may be skipped due to missing credentials.")
    else:
        print("✓ All required environment variables are set")