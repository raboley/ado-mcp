#!/usr/bin/env python3
"""
Script to fix undefined variable issues in tests after API parameter changes.
This fixes instances where variables like project_id, pipeline_id are used but not defined.
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
    # Define the replacements for undefined variables and quote fixes
    replacements = [
        # Fix undefined project_id variables - make sure they call get_project_id()
        (r'(\s+)result = await mcp_client\.call_tool\(\s*\n\s*"([^"]+)",\s*\{"project_id":\s*project_id,([^}]*)\}\s*\)',
         r'\1project_id = get_project_id()\n\1result = await mcp_client.call_tool(\n\1    "\2", {"project_id": project_id,\3}\n\1)'),
        
        # Fix quote issues in f-strings with await calls
        (r'await get_pipeline_id_by_name\(mcp_client, "([^"]+)"\)', 
         r"await get_pipeline_id_by_name(mcp_client, '\1')"),
        
        # Fix cases where pipeline_name variables are defined but call uses different names
        (r'pipeline_name = "([^"]+)"\s*\n.*?"get_pipeline", \{"project_name": get_project_name\(\), "pipeline_name": "test_run_and_get_pipeline_run_details"\}',
         r'pipeline_name = "\1"\n    result = await mcp_client.call_tool(\n        "get_pipeline", {"project_name": get_project_name(), "pipeline_name": "\1"}'),
         
        # Fix cases where wrong pipeline names are used in run_pipeline calls
        (r'pipeline_name = "([^"]+)"\s*.*?run_pipeline.*?"pipeline_name": "test_run_and_get_pipeline_run_details"',
         r'pipeline_name = "\1"\n    # Use the correct pipeline name\n    result = await mcp_client.call_tool(\n        "run_pipeline", {"project_name": get_project_name(), "pipeline_name": "\1"}'),
    ]
    
    # Files that need to be updated (based on the failing tests)
    target_files = [
        'tests/logs/test_get_pipeline_failure_summary.py', 
        'tests/pipeline_runs/test_get_pipeline_run.py',
        'tests/pipeline_runs/test_run_pipeline_with_parameters.py',
        'tests/pipelines/test_get_pipeline.py',
        'tests/preview/test_preview_pipeline_basic.py',
        'tests/preview/test_preview_pipeline_github_resources.py',
        'tests/preview/test_preview_pipeline_yaml_override.py',
    ]
    
    updated_files = []
    
    for file_path in target_files:
        if os.path.exists(file_path):
            if replace_in_file(file_path, replacements):
                updated_files.append(file_path)
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nUpdated {len(updated_files)} files:")
    for file_path in updated_files:
        print(f"  - {file_path}")


if __name__ == "__main__":
    main()