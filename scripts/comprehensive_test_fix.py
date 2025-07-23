#!/usr/bin/env python3
"""
Comprehensive fix script for test conversion issues.

Fixes:
1. Missing import statements
2. Missing helper function definitions
3. Remaining hardcoded function calls
4. Import order and cleanup
"""

import os
import re
import subprocess
from pathlib import Path


# Helper function template
HELPER_FUNCTION = '''
async def get_pipeline_id_by_name(mcp_client: Client, pipeline_name: str) -> int:
    """Helper function to get pipeline ID by name using MCP tools."""
    project_name = get_project_name()
    
    result = await mcp_client.call_tool("find_pipeline_by_name", {
        "project_name": project_name,
        "pipeline_name": pipeline_name
    })
    
    pipeline_info = result.data
    if not pipeline_info or "pipeline" not in pipeline_info:
        raise ValueError(f"Pipeline '{pipeline_name}' not found in project '{project_name}'")
    
    return pipeline_info["pipeline"]["id"]
'''

# Mapping of old function names to pipeline names
FUNCTION_TO_PIPELINE_MAPPING = {
    'get_test_basic_pipeline_id()': 'await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")',
    'get_basic_pipeline_id()': 'await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")',
    'get_test_github_resources_pipeline_id()': 'await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")',
    'get_github_resources_pipeline_id()': 'await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")',
    'get_test_parameterized_pipeline_id()': 'await get_pipeline_id_by_name(mcp_client, "preview-test-parameterized")',
    'get_parameterized_pipeline_id()': 'await get_pipeline_id_by_name(mcp_client, "preview-test-parameterized")',
    'get_preview_pipeline_id()': 'await get_pipeline_id_by_name(mcp_client, "preview-test-valid")',
    'get_failing_pipeline_id()': 'await get_pipeline_id_by_name(mcp_client, "log-test-failing")',
    'get_complex_pipeline_id()': 'await get_pipeline_id_by_name(mcp_client, "slow.log-test-complex")',
    'get_runtime_variables_pipeline_id()': 'await get_pipeline_id_by_name(mcp_client, "runtime-variables-test")',
    'get_test_project_id()': 'get_project_id()'
}


def ensure_imports(content):
    """Ensure all required imports are present."""
    imports_to_add = []
    
    if 'pytest' in content and 'import pytest' not in content:
        imports_to_add.append('import pytest')
    
    if 'logging' in content and 'import logging' not in content:
        imports_to_add.append('import logging')
        
    if 'time' in content and 'import time' not in content:
        imports_to_add.append('import time')
    
    if 'Client' in content and 'from fastmcp.client import Client' not in content:
        imports_to_add.append('from fastmcp.client import Client')
    
    if imports_to_add:
        # Find the first import line
        lines = content.split('\n')
        import_insert_idx = 0
        
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_insert_idx = i
                break
        
        # Insert new imports after existing ones
        for imp in imports_to_add:
            lines.insert(import_insert_idx + 1, imp)
            import_insert_idx += 1
        
        content = '\n'.join(lines)
    
    return content


def ensure_helper_function(content):
    """Ensure the helper function is present if get_pipeline_id_by_name is used."""
    if 'get_pipeline_id_by_name(' in content and 'async def get_pipeline_id_by_name' not in content:
        # Find where to insert the helper function (after mcp_client fixture)
        fixture_pattern = r'(@pytest\.fixture[^}]*?async def mcp_client[^}]*?yield client)'
        fixture_match = re.search(fixture_pattern, content, re.DOTALL)
        
        if fixture_match:
            # Add helper function after fixture
            replacement = fixture_match.group(1) + HELPER_FUNCTION
            content = content.replace(fixture_match.group(1), replacement)
        else:
            # Add after imports if no fixture found
            lines = content.split('\n')
            insert_idx = 0
            
            for i, line in enumerate(lines):
                if line.startswith('pytestmark = '):
                    insert_idx = i + 1
                    break
            
            if insert_idx > 0:
                lines.insert(insert_idx, HELPER_FUNCTION)
                content = '\n'.join(lines)
    
    return content


def replace_function_calls(content):
    """Replace old function calls with new implementations."""
    for old_call, new_call in FUNCTION_TO_PIPELINE_MAPPING.items():
        content = content.replace(old_call, new_call)
    
    return content


def fix_test_file(file_path):
    """Fix a single test file comprehensively."""
    print(f"Fixing {file_path}...")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all fixes
        content = ensure_imports(content)
        content = ensure_helper_function(content)  
        content = replace_function_calls(content)
        
        # Clean up multiple blank lines
        content = re.sub(r'\n\n\n+', '\n\n', content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  ✅ Fixed {file_path}")
        else:
            print(f"  ⏭️  No fixes needed for {file_path}")
    
    except Exception as e:
        print(f"  ❌ Error fixing {file_path}: {e}")


def find_test_files():
    """Find all Python test files."""
    test_files = []
    
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                test_files.append(os.path.join(root, file))
    
    return test_files


def main():
    """Fix all test files comprehensively."""
    print("🔧 Applying comprehensive fixes to test files...")
    print()
    
    test_files = find_test_files()
    print(f"Found {len(test_files)} test files to fix")
    print()
    
    for file_path in test_files:
        fix_test_file(file_path)
    
    print()
    print("🎉 Comprehensive fixes complete!")
    print("📝 Next steps:")
    print("  1. Run tests to verify fixes: task test")
    print("  2. Check for any remaining issues in test output")


if __name__ == "__main__":
    main()