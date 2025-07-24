#!/usr/bin/env python3
"""
Script to correctly fix test_server.py to use name-based API parameters only for tools that exist.
For tools that don't have name-based equivalents, we'll use the ID-based tools but get the IDs from names.
"""

import re

def main():
    file_path = "tests/test_server.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Revert the non-existent tools back to their original forms but with proper ID resolution
    replacements = [
        # Revert get_pipeline_timeline_by_name back to get_pipeline_timeline
        (r'"get_pipeline_timeline_by_name", \{"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id\}',
         r'"get_pipeline_timeline", {"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id}'),
        
        # Revert list_pipeline_logs_by_name back to list_pipeline_logs  
        (r'"list_pipeline_logs_by_name", \{"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id\}',
         r'"list_pipeline_logs", {"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id}'),
        
        # Revert get_log_content_by_id_by_name back to get_log_content_by_id
        (r'"get_log_content_by_id_by_name", \{"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id, "log_id": log_id\}',
         r'"get_log_content_by_id", {"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id, "log_id": log_id}'),
        
        # Revert get_pipeline_by_name back to get_pipeline (this doesn't exist either)
        (r'"get_pipeline_by_name", \{"project_name": project_name, "pipeline_name": pipeline_name\}',
         r'"get_pipeline", {"project_name": project_name, "pipeline_name": pipeline_name}'),
        
        # Revert get_pipeline_run_by_name back to get_pipeline_run (this doesn't exist either)
        (r'"get_pipeline_run_by_name", \{"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id\}',
         r'"get_pipeline_run", {"project_name": project_name, "pipeline_name": pipeline_name, "run_id": run_id}'),
        
        # Revert delete_pipeline_by_name back to delete_pipeline (this doesn't exist either)
        (r'"delete_pipeline_by_name", \{"project_name": project_name, "pipeline_name": pipeline_name\}',
         r'"delete_pipeline", {"project_name": project_name, "pipeline_name": pipeline_name}'),
        
        # Revert preview_pipeline_by_name back to preview_pipeline (this doesn't exist either)
        (r'"preview_pipeline_by_name", \{"project_name": project_name, "pipeline_name": pipeline_name\}',
         r'"preview_pipeline", {"project_name": project_name, "pipeline_name": pipeline_name}'),
        
        # Fix the nonexistent pipeline test
        (r'pipeline_id = 99999  # Non-existent pipeline ID',
         r'pipeline_name = "nonexistent-pipeline"  # Non-existent pipeline name'),
        
        # Fix any remaining usage of that undefined pipeline_id
        (r'"preview_pipeline_by_name", \{"project_name": project_name, "pipeline_name": pipeline_name\}',
         r'"preview_pipeline", {"project_name": project_name, "pipeline_name": pipeline_name}'),
    ]
    
    # Apply replacements
    for pattern, replacement in replacements:
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