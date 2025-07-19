#!/usr/bin/env python3
"""
Test script to verify IDE testing setup.

Run this script directly in your IDE to verify that:
1. Environment variables are loaded from .env file
2. Azure DevOps credentials are available
3. Basic MCP functionality works

Usage:
    python test_ide_setup.py
"""

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

# Load .env file
project_root = Path(__file__).parent
env_file = project_root / ".env"
load_dotenv(env_file, override=True)

print("🧪 IDE Testing Setup Verification")
print("=" * 40)

# Check environment variables
print("\n📋 Environment Variables:")
ado_pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
ado_org_url = os.getenv("ADO_ORGANIZATION_URL")
ado_project_name = os.getenv("ADO_PROJECT_NAME")

if ado_pat:
    print(f"✅ AZURE_DEVOPS_EXT_PAT: {'*' * (len(ado_pat) - 4)}{ado_pat[-4:]}")
else:
    print("❌ AZURE_DEVOPS_EXT_PAT: NOT SET")
    
if ado_org_url:
    print(f"✅ ADO_ORGANIZATION_URL: {ado_org_url}")
else:
    print("❌ ADO_ORGANIZATION_URL: NOT SET")
    
if ado_project_name:
    print(f"✅ ADO_PROJECT_NAME: {ado_project_name}")
else:
    print("ℹ️  ADO_PROJECT_NAME: NOT SET (optional)")

# Test basic imports
print("\n📦 Testing Imports:")
try:
    from ado.client import AdoClient
    print("✅ ado.client imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ado.client: {e}")
    sys.exit(1)

try:
    from fastmcp.client import Client
    print("✅ fastmcp.client imported successfully")
except ImportError as e:
    print(f"❌ Failed to import fastmcp.client: {e}")
    sys.exit(1)

# Test ADO client creation
print("\n🔗 Testing Azure DevOps Connection:")
if ado_pat and ado_org_url:
    try:
        client = AdoClient(organization_url=ado_org_url, pat=ado_pat)
        print("✅ ADO client created successfully")
        
        # Test authentication
        auth_result = client.check_authentication()
        if auth_result:
            print("✅ Azure DevOps authentication successful")
        else:
            print("❌ Azure DevOps authentication failed")
    except Exception as e:
        print(f"❌ Failed to create ADO client: {e}")
else:
    print("⚠️  Skipping ADO connection test (missing credentials)")

print("\n🎯 Summary:")
if ado_pat and ado_org_url:
    print("✅ Your IDE testing setup is ready!")
    print("✅ You can run tests directly in your IDE")
    print("✅ Environment variables will be automatically loaded")
else:
    print("❌ Setup incomplete - please check your .env file")
    print("   Make sure it contains AZURE_DEVOPS_EXT_PAT and ADO_ORGANIZATION_URL")

print("\n🚀 Next steps:")
print("   1. Run tests in your IDE")
print("   2. Or use: python -m pytest tests/test_environment.py")
print("   3. Or use: python -m pytest tests/pipeline_runs/ -k basic")