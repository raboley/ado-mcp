"""
Graceful cancellation handling for MCP tools.

This module provides decorators and utilities to handle cancellation
gracefully, converting technical stack traces into user-friendly messages.
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Dict, Optional

logger = logging.getLogger(__name__)


class GracefulCancellationError(Exception):
    """Clean exception for user-facing cancellation messages."""
    
    def __init__(self, message: str = "Operation cancelled by user"):
        self.message = message
        super().__init__(message)
    
    def __str__(self) -> str:
        return self.message


def graceful_cancellation(
    operation_name: Optional[str] = None,
    cleanup_message: Optional[str] = None
):
    """
    Decorator that wraps tool functions with graceful cancellation handling.
    
    This decorator catches various cancellation exceptions and converts them
    into clean, user-friendly messages instead of showing stack traces.
    
    Args:
        operation_name: Name of the operation for better error messages
        cleanup_message: Custom message to show during cleanup
    
    Example:
        @graceful_cancellation("pipeline execution")
        async def run_pipeline(...):
            # Long running operation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            func_name = operation_name or func.__name__
            
            try:
                return await func(*args, **kwargs)
                
            except asyncio.CancelledError:
                # Clean asyncio cancellation
                logger.info(f"Operation '{func_name}' was cancelled by user")
                raise GracefulCancellationError(
                    f"⚠️ {func_name.replace('_', ' ').title()} was cancelled"
                )
                
            except KeyboardInterrupt:
                # Direct keyboard interrupt (Ctrl+C)
                logger.info(f"Operation '{func_name}' interrupted by user")
                raise GracefulCancellationError(
                    f"⚠️ {func_name.replace('_', ' ').title()} was interrupted"
                )
                
            except SystemExit:
                # System exit signal
                logger.info(f"Operation '{func_name}' received exit signal")
                raise GracefulCancellationError(
                    f"⚠️ {func_name.replace('_', ' ').title()} was stopped"
                )
                
            except Exception as e:
                # Check if this is a nested cancellation exception
                if _is_cancellation_exception(e):
                    logger.info(f"Operation '{func_name}' cancelled (nested exception)")
                    raise GracefulCancellationError(
                        f"⚠️ {func_name.replace('_', ' ').title()} was cancelled"
                    )
                
                # Re-raise non-cancellation exceptions as-is
                raise
                
        return wrapper
    return decorator


def _is_cancellation_exception(exception: Exception) -> bool:
    """
    Check if an exception is related to cancellation.
    
    This looks for various indicators that suggest the exception
    was caused by user cancellation or system interruption.
    """
    exc_str = str(exception).lower()
    exc_type = type(exception).__name__.lower()
    
    # Check exception type names
    cancellation_types = [
        'cancelledror', 'keyboardinterrupt', 'systemexxit',
        'baseexceptiongroup', 'exceptiongroup'
    ]
    
    if any(cancel_type in exc_type for cancel_type in cancellation_types):
        return True
    
    # Check exception message content
    cancellation_indicators = [
        'cancelled', 'interrupted', 'keyboard interrupt',
        'operation cancelled', 'task cancelled', 'sigint',
        'unhandled errors in a taskgroup', 'baseexceptiongroup'
    ]
    
    if any(indicator in exc_str for indicator in cancellation_indicators):
        return True
    
    # Check for nested cancellation in exception groups
    if hasattr(exception, 'exceptions'):
        # Handle ExceptionGroup and BaseExceptionGroup
        try:
            for nested_exc in exception.exceptions:
                if _is_cancellation_exception(nested_exc):
                    return True
        except (AttributeError, TypeError):
            pass
    
    # Check __cause__ and __context__ for nested cancellation
    if hasattr(exception, '__cause__') and exception.__cause__:
        if _is_cancellation_exception(exception.__cause__):
            return True
    
    if hasattr(exception, '__context__') and exception.__context__:
        if _is_cancellation_exception(exception.__context__):
            return True
    
    return False


def handle_tool_cancellation(tool_name: str) -> Callable:
    """
    Convenience wrapper for MCP tool cancellation handling.
    
    This is a simplified version of graceful_cancellation specifically
    designed for MCP tools with consistent naming conventions.
    
    Args:
        tool_name: The name of the MCP tool
    
    Example:
        @handle_tool_cancellation("run_pipeline_and_get_outcome_by_name")
        async def run_pipeline_and_get_outcome_by_name(...):
            pass
    """
    # Convert snake_case to human readable
    display_name = tool_name.replace('_', ' ').replace(' and ', ' & ').title()
    
    return graceful_cancellation(
        operation_name=display_name.lower(),
        cleanup_message=f"Cleaning up {display_name.lower()}..."
    )


async def with_cancellation_handling(
    coro: Callable,
    operation_name: str,
    *args,
    **kwargs
) -> Any:
    """
    Execute a coroutine with cancellation handling.
    
    This is a functional approach for cases where decorators aren't suitable.
    
    Args:
        coro: The coroutine function to execute
        operation_name: Name for error messages
        *args: Arguments to pass to the coroutine
        **kwargs: Keyword arguments to pass to the coroutine
    
    Returns:
        The result of the coroutine execution
        
    Raises:
        GracefulCancellationError: If the operation is cancelled
    """
    try:
        return await coro(*args, **kwargs)
        
    except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
        logger.info(f"Operation '{operation_name}' was cancelled")
        raise GracefulCancellationError(
            f"⚠️ {operation_name.replace('_', ' ').title()} was cancelled"
        )
        
    except Exception as e:
        if _is_cancellation_exception(e):
            logger.info(f"Operation '{operation_name}' cancelled (nested exception)")
            raise GracefulCancellationError(
                f"⚠️ {operation_name.replace('_', ' ').title()} was cancelled"
            )
        raise


# Tool-specific handlers for high-risk operations
def handle_pipeline_cancellation(func: Callable) -> Callable:
    """Specialized cancellation handler for pipeline operations."""
    return graceful_cancellation("pipeline operation")(func)


def handle_build_cancellation(func: Callable) -> Callable:
    """Specialized cancellation handler for build operations.""" 
    return graceful_cancellation("build operation")(func)


def handle_deployment_cancellation(func: Callable) -> Callable:
    """Specialized cancellation handler for deployment operations."""
    return graceful_cancellation("deployment operation")(func)