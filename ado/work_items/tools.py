"""MCP tool definitions for Azure DevOps Work Items."""

import logging

from ado.work_items.batch_operations import register_batch_tools
from ado.work_items.comments_and_history import register_comment_tools
from ado.work_items.crud_operations import register_crud_tools
from ado.work_items.query_operations import register_query_tools
from ado.work_items.type_introspection import register_type_tools

logger = logging.getLogger(__name__)


def register_work_item_tools(mcp_instance, client_container):
    """
    Register work item related tools with the FastMCP instance.

    Args:
        mcp_instance: The FastMCP instance to register tools with.
        client_container: Dictionary holding the AdoClient instance.
    """

    # Register CRUD operations from separate module
    register_crud_tools(mcp_instance, client_container)

    # Register type introspection tools from separate module
    register_type_tools(mcp_instance, client_container)

    # Register query operations from separate module
    register_query_tools(mcp_instance, client_container)

    # Register batch operations from separate module
    register_batch_tools(mcp_instance, client_container)

    # Register comment and history operations from separate module
    register_comment_tools(mcp_instance, client_container)
