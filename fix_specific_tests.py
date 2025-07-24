#!/usr/bin/env python3
"""
Script to fix specific tests to use the new name-based API parameters.
This script targets the tests that are currently failing due to API changes.
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
    # Define the core tool signature replacements
    core_tool_replacements = [
        # get_pipeline - change from ID-based to name-based
        (r'"get_pipeline",\s*\{\s*"project_id":\s*([^,}]+),\s*"pipeline_id":\s*([^}]+)\}',
         r'"get_pipeline", {"project_name": get_project_name(), "pipeline_name": "test_run_and_get_pipeline_run_details"}'),
        
        # get_pipeline_run - change from ID-based to name-based
        (r'"get_pipeline_run",\s*\{\s*"project_id":\s*([^,}]+),\s*"pipeline_id":\s*([^,}]+),\s*"run_id":\s*([^}]+)\}',
         r'"get_pipeline_run", {"project_name": get_project_name(), "pipeline_name": "test_run_and_get_pipeline_run_details", "run_id": \3}'),
        
        # get_pipeline_failure_summary - change from ID-based to name-based
        (r'"get_pipeline_failure_summary",\s*\{\s*"project_id":\s*([^,}]+),\s*"pipeline_id":\s*([^,}]+),\s*"run_id":\s*([^,}]+)([^}]*)\}',
         r'"get_pipeline_failure_summary", {"project_name": get_project_name(), "pipeline_name": "test_run_and_get_pipeline_run_details", "run_id": \3\4}'),
        
        # get_build_by_id - this stays as ID-based since it's about build IDs
        # No change needed for get_build_by_id
        
        # run_pipeline - change from ID-based to name-based
        (r'"run_pipeline",\s*\{\s*"project_id":\s*([^,}]+),\s*"pipeline_id":\s*([^,}]+)([^}]*)\}',
         r'"run_pipeline", {"project_name": get_project_name(), "pipeline_name": "test_run_and_get_pipeline_run_details"\3}'),
        
        # Remove pipeline_id lookups when they can be replaced with static names
        (r'pipeline_id\s*=\s*await\s+get_pipeline_id_by_name\([^,]+,\s*"([^"]+)"\)\s*\n',
         r'pipeline_name = "\1"\n'),
        
        # Change project_id = get_project_id() to project_name = get_project_name()
        (r'project_id\s*=\s*get_project_id\(\)',
         r'project_name = get_project_name()'),
    ]
    
    # Files that need to be updated (based on the failing tests)
    target_files = [
        'tests/builds/test_get_build_by_id.py',
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
            if replace_in_file(file_path, core_tool_replacements):
                updated_files.append(file_path)
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nUpdated {len(updated_files)} files:")
    for file_path in updated_files:
        print(f"  - {file_path}")


if __name__ == "__main__":
    main()