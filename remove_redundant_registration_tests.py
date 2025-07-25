#!/usr/bin/env python3
"""Script to remove redundant registration tests that are now covered by comprehensive test."""

import re
import os

# Define the registration tests to remove
tests_to_remove = [
    # Organization & Authentication
    ("tests/organization/test_check_authentication.py", "test_check_authentication_tool_registration"),
    
    # Project Management  
    ("tests/projects/test_list_projects.py", "test_list_projects_tool_registration"),
    ("tests/tools/test_projects.py", "test_enhanced_project_tools_are_registered"),
    ("tests/tools/test_enhanced_project_tools.py", "test_enhanced_project_tools_are_registered"),
    
    # Pipeline Management
    ("tests/pipelines/test_list_pipelines.py", "test_list_pipelines_tool_registration"),
    ("tests/pipelines/test_get_pipeline.py", "test_get_pipeline_tool_registration"),
    
    # Pipeline Execution
    ("tests/pipeline_runs/test_run_pipeline.py", "test_run_pipeline_tool_registration"),
    ("tests/pipeline_runs/test_run_pipeline_by_name.py", "test_run_pipeline_by_name_tool_registration"),
    ("tests/pipeline_runs/test_run_pipeline_with_parameters.py", "test_run_pipeline_parameter_combinations_tool_registration"),
    ("tests/pipeline_runs/test_get_pipeline_run.py", "test_get_pipeline_run_tool_registration"),
    ("tests/preview/test_preview_pipeline_basic.py", "test_preview_pipeline_tool_registration"),
    
    # Build & Log Analysis
    ("tests/builds/test_get_build_by_id.py", "test_get_build_by_id_tool_registration"),
    ("tests/logs/test_get_pipeline_failure_summary.py", "test_get_pipeline_failure_summary_tool_registration"),
    
    # Service Connections
    ("tests/service_connections/test_list_service_connections.py", "test_list_service_connections_tool_registration"),
    
    # Work Item CRUD
    ("tests/work_items/test_crud_operations.py", "test_work_item_tools_registered_in_mcp_server"),
    ("tests/work_items/test_crud_operations.py", "test_list_work_items_tool_registered_in_mcp_server"),
    
    # Work Item Batch Operations
    ("tests/work_items/test_batch_operations.py", "test_get_work_items_batch_tool_registration"),
    ("tests/work_items/test_batch_updates.py", "test_update_work_items_batch_tool_registration"),
    ("tests/work_items/test_batch_deletion.py", "test_delete_work_items_batch_tool_registration"),
    
    # Work Item Queries
    ("tests/work_items/test_convenience_queries.py", "test_get_my_work_items_tool_registration"),
    ("tests/work_items/test_convenience_queries.py", "test_get_recent_work_items_tool_registration"),
    
    # Work Item Metadata & Types
    ("tests/work_items/test_metadata.py", "test_metadata_tools_registered_in_mcp_server"),
    ("tests/work_items/test_enhanced_types.py", "test_enhanced_type_tools_registered_in_mcp_server"),
    
    # Work Item Comments & History
    ("tests/work_items/test_comments_history.py", "test_add_work_item_comment_tool_registration"),
    ("tests/work_items/test_comments_history.py", "test_get_work_item_comments_tool_registration"),
    ("tests/work_items/test_comments_history.py", "test_get_work_item_history_tool_registration"),
    
    # Work Item Relationships
    ("tests/work_items/test_relationships.py", "test_link_work_items_tool_registration"),
    ("tests/work_items/test_relationships.py", "test_get_work_item_relations_tool_registration"),
    
    # Process & Templates
    ("tests/processes/test_processes.py", "test_process_tools_registered_in_mcp_server"),
    
    # Test Server Duplicates
    ("tests/test_server.py", "test_run_pipeline_and_get_outcome_tool_registration"),
    ("tests/test_server.py", "test_get_build_by_id_tool_registration"),
    
    # Helper & Utility
    ("tests/test_helpers.py", "test_helper_tools_tool_registration"),
]

def remove_test_function(file_path, function_name):
    """Remove a test function from a Python file."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the function definition and remove it along with its body
    # Pattern to match async def or def function with any decorators
    escaped_name = re.escape(function_name)
    pattern = f'(?:@[^\\n]*\\n)*(?:async\\s+)?def\\s+{escaped_name}\\s*\\([^)]*\\):.*?(?=\\n(?:@[^\\n]*\\n)*(?:async\\s+)?def|\\n(?:class\\s+|\\n*$)|\\Z)'
    
    # First try to find the function
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if not match:
        # Try a simpler pattern for the function
        pattern = f'(?:async\\s+)?def\\s+{escaped_name}\\s*\\([^)]*\\):.*?(?=\\n(?:async\\s+)?def|\\nclass\\s+|\\n*$|\\Z)'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    
    if match:
        # Remove the matched function
        new_content = content[:match.start()] + content[match.end():]
        # Clean up extra newlines
        new_content = re.sub(r'\n\n\n+', '\n\n', new_content)
        
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"✅ Removed {function_name} from {file_path}")
        return True
    else:
        print(f"⚠️  Function {function_name} not found in {file_path}")
        return False

def main():
    """Remove all redundant registration tests."""
    print("🧹 Removing redundant registration tests...")
    print("=" * 60)
    
    removed_count = 0
    not_found_count = 0
    
    for file_path, function_name in tests_to_remove:
        if remove_test_function(file_path, function_name):
            removed_count += 1
        else:
            not_found_count += 1
    
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   ✅ Removed: {removed_count} registration tests")
    print(f"   ⚠️  Not found: {not_found_count} tests")
    print(f"   📁 Total processed: {len(tests_to_remove)} test functions")
    
    print("\n🔍 Verifying changes...")
    
if __name__ == "__main__":
    main()