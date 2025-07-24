#!/usr/bin/env python3
"""
Script to systematically fix test_server.py to use the new name-based API parameters.
This converts all old API calls from ID-based to name-based parameters.
"""

import re

def main():
    file_path = "tests/test_server.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Define the replacements for converting to name-based API calls
    replacements = [
        # Fix project_id = get_project_id() to project_name = get_project_name()
        (r'(\s+)project_id = get_project_id\(\)', r'\1project_name = get_project_name()'),
        
        # Fix pipeline_id = await get_pipeline_id_by_name() to pipeline_name = "pipeline-name"
        (r'(\s+)pipeline_id = await get_pipeline_id_by_name\(mcp_client, "([^"]+)"\)', r'\1pipeline_name = "\2"'),
        
        # Fix basic run_pipeline calls
        (r'"run_pipeline",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id', 
         r'"run_pipeline_by_name", {"project_name": project_name, "pipeline_name": pipeline_name'),
        
        # Fix run_pipeline_and_get_outcome calls  
        (r'"run_pipeline_and_get_outcome",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id',
         r'"run_pipeline_and_get_outcome_by_name", {"project_name": project_name, "pipeline_name": pipeline_name'),
        
        # Fix get_pipeline calls
        (r'"get_pipeline",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id\s*\}',
         r'"get_pipeline_by_name", {"project_name": project_name, "pipeline_name": pipeline_name}'),
        
        # Fix get_pipeline_run calls
        (r'"get_pipeline_run",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id,\s*"run_id":\s*run_id\s*\}',
         r'"get_pipeline_run_by_name", {"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id}'),
        
        # Fix get_pipeline_timeline calls
        (r'"get_pipeline_timeline",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id,\s*"run_id":\s*run_id\s*\}',
         r'"get_pipeline_timeline_by_name", {"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id}'),
        
        # Fix get_pipeline_failure_summary calls
        (r'"get_pipeline_failure_summary",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id,\s*"run_id":\s*run_id',
         r'"get_pipeline_failure_summary_by_name", {"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id'),
        
        # Fix list_pipeline_logs calls
        (r'"list_pipeline_logs",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id,\s*"run_id":\s*run_id\s*\}',
         r'"list_pipeline_logs_by_name", {"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id}'),
        
        # Fix get_log_content_by_id calls
        (r'"get_log_content_by_id",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id,\s*"run_id":\s*run_id,\s*"log_id":\s*log_id\s*\}',
         r'"get_log_content_by_id_by_name", {"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id, "log_id": log_id}'),
        
        # Fix preview_pipeline calls
        (r'"preview_pipeline",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id\s*\}',
         r'"preview_pipeline_by_name", {"project_name": project_name, "pipeline_name": pipeline_name}'),
        
        # Fix delete_pipeline calls
        (r'"delete_pipeline",\s*\{\s*"project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id\s*\}',
         r'"delete_pipeline_by_name", {"project_name": project_name, "pipeline_name": pipeline_name}'),
        
        # Fix calls with additional parameters like timeout_seconds
        (r'("project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id,\s*"timeout_seconds":\s*\d+)',
         lambda m: m.group(1).replace('"project_id": project_id', '"project_name": project_name').replace('"pipeline_id": pipeline_id', '"pipeline_name": pipeline_name')),
        
        # Fix calls with yaml_override
        (r'("project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id,\s*"yaml_override":\s*yaml_override)',
         lambda m: m.group(1).replace('"project_id": project_id', '"project_name": project_name').replace('"pipeline_id": pipeline_id', '"pipeline_name": pipeline_name')),
        
        # Fix calls with variables
        (r'("project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id,\s*"variables":\s*variables)',
         lambda m: m.group(1).replace('"project_id": project_id', '"project_name": project_name').replace('"pipeline_id": pipeline_id', '"pipeline_name": pipeline_name')),
        
        # Fix calls with max_lines parameter
        (r'("project_id":\s*project_id,\s*"pipeline_id":\s*pipeline_id,\s*"run_id":\s*run_id,\s*"max_lines":\s*\d+)',
         lambda m: m.group(1).replace('"project_id": project_id', '"project_name": project_name').replace('"pipeline_id": pipeline_id', '"pipeline_name": pipeline_name')),
    ]
    
    # Apply replacements
    for pattern, replacement in replacements:
        if callable(replacement):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Write the updated content back to the file
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ Updated {file_path}")
        
        # Count the number of lines changed
        original_lines = original_content.split('\n')
        new_lines = content.split('\n')
        changes = 0
        for i, (old, new) in enumerate(zip(original_lines, new_lines)):
            if old != new:
                changes += 1
        print(f"📊 Changed {changes} lines")
    else:
        print(f"ℹ️  No changes needed in {file_path}")

if __name__ == "__main__":
    main()