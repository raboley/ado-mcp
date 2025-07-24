#!/usr/bin/env python3
"""
Script to fix all remaining API parameter and undefined variable issues in tests.
This script systematically finds and fixes common issues after the API parameter changes.
"""

import os
import re
import glob


def replace_in_file(file_path, replacements):
    """Apply multiple replacements to a file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    for old_pattern, new_pattern in replacements:
        content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE | re.DOTALL)
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Updated: {file_path}")
        return True
    return False


def main():
    # Define the replacements for common issues
    replacements = [
        # Fix any remaining project_id/pipeline_id API calls that weren't caught
        (r'"([^"]+)",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id([^}]*)\}',
         r'"\1", {"project_name": project_name, "pipeline_name": pipeline_name\2}'),
        
        # Fix calls with hardcoded IDs that should use names
        (r'"([^"]+)",\s*\{\s*"project_id":\s*([^,}]+),\s*"pipeline_id":\s*([^,}]+)([^}]*)\}',
         r'"\1", {"project_name": get_project_name(), "pipeline_name": pipeline_name\4}'),
         
        # Fix undefined pipeline_id assertions - replace with actual lookup
        (r'assert.*pipeline_run\["pipeline"\]\["id"\]\s*==\s*pipeline_id,\s*\(\s*f"Expected pipeline ID \{pipeline_id\}.*?\)',
         r'expected_pipeline_id = await get_pipeline_id_by_name(mcp_client, pipeline_name)\n    assert pipeline_run["pipeline"]["id"] == expected_pipeline_id, (\n        f"Expected pipeline ID {expected_pipeline_id} but got {pipeline_run[\'pipeline\'][\'id\']}"'),
        
        # Fix remaining quote issues in get_pipeline_id_by_name calls
        (r'get_pipeline_id_by_name\(mcp_client, "([^"]+)"\)', 
         r"get_pipeline_id_by_name(mcp_client, '\1')"),
         
        # Fix any remaining undefined project_id usage
        (r'(\s+)(result = await mcp_client\.call_tool\(\s*\n\s*"[^"]+",\s*\{[^}]*"project_id":\s*project_id)',
         r'\1project_id = get_project_id()\n\1\2'),
        
        # Fix undefined pipeline_id usage in variable assignments
        (r'(\s+)pipeline_id\s*=\s*pipeline_id([,\s])',
         r'\1pipeline_id = await get_pipeline_id_by_name(mcp_client, pipeline_name)\2'),
    ]
    
    # Files to check for remaining issues
    test_files = []
    for pattern in ['tests/**/*.py', 'tests/*.py']:
        test_files.extend(glob.glob(pattern, recursive=True))
    
    updated_files = []
    
    for file_path in test_files:
        if os.path.exists(file_path):
            if replace_in_file(file_path, replacements):
                updated_files.append(file_path)
    
    print(f"\nUpdated {len(updated_files)} files:")
    for file_path in updated_files:
        print(f"  - {file_path}")


if __name__ == "__main__":
    main()