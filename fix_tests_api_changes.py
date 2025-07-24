#!/usr/bin/env python3
"""
Script to fix all tests to use the new name-based API parameters.

This script converts old ID-based API calls to name-based ones:
- project_id -> project_name 
- pipeline_id -> pipeline_name
- Updates function calls accordingly
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
        content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE)
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Updated: {file_path}")
        return True
    return False

def main():
    # Define the replacements for the main tools that now use name-based parameters
    replacements = [
        # run_pipeline_and_get_outcome calls
        (r'"run_pipeline_and_get_outcome",\s*\{\s*"project_id":\s*([^,}]+),\s*"pipeline_id":\s*([^,}]+)([^}]*)\}',
         r'"run_pipeline_and_get_outcome", {"project_name": get_project_name(), "pipeline_name": "test_run_and_get_pipeline_run_details"\3}'),
        
        # run_pipeline calls - this is trickier because we need to know the pipeline name
        (r'"run_pipeline",\s*\{\s*"project_id":\s*([^,}]+),\s*"pipeline_id":\s*([^,}]+)([^}]*)\}',
         r'"run_pipeline", {"project_name": get_project_name(), "pipeline_name": "test_run_and_get_pipeline_run_details"\3}'),
        
        # Simple project_id/pipeline_id variable usage - need to be more careful here
        (r'project_id\s*=\s*get_project_id\(\)',
         r'project_name = get_project_name()'),
        
        # Remove pipeline_id lookups when we can determine the pipeline name
        (r'pipeline_id\s*=\s*await\s+get_pipeline_id_by_name\([^,]+,\s*"([^"]+)"\)',
         r'pipeline_name = "\1"'),
    ]
    
    # Find all test files 
    test_files = []
    for pattern in ['tests/**/*.py', 'tests/*.py']:
        test_files.extend(glob.glob(pattern, recursive=True))
    
    updated_files = []
    
    for file_path in test_files:
        if replace_in_file(file_path, replacements):
            updated_files.append(file_path)
    
    print(f"\nUpdated {len(updated_files)} files:")
    for file_path in updated_files:
        print(f"  - {file_path}")

if __name__ == "__main__":
    main()