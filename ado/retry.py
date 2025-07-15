"""Retry mechanism with exponential backoff for ADO API calls."""

import time
import random
import logging
from typing import Any, Callable, Optional, Type, Tuple
from functools import wraps

import requests
from opentelemetry import trace

from .config import RetryConfig
from .errors import AdoRateLimitError, AdoTimeoutError, AdoNetworkError

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class RetryManager:
    """
    Manages retry logic with exponential backoff for ADO API calls.
    
    This class provides intelligent retry handling for different types of failures:
    - Rate limiting (429 errors) with respect for Retry-After headers
    - Network errors with exponential backoff
    - Timeout handling
    - Circuit breaker pattern for persistent failures
    """
    
    def __init__(self, config: RetryConfig):
        """
        Initialize retry manager with configuration.
        
        Args:
            config: Retry configuration settings
        """
        self.config = config
        self._failure_count = 0
        self._circuit_open = False
        self._last_failure_time = 0
        self._circuit_timeout = 60  # seconds
        
    def _calculate_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """
        Calculate delay for next retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            retry_after: Optional retry-after value from server
            
        Returns:
            float: Delay in seconds
        """
        if retry_after:
            # Respect server's retry-after header
            base_delay = retry_after
        else:
            # Calculate exponential backoff
            base_delay = min(
                self.config.initial_delay * (self.config.backoff_multiplier ** attempt),
                self.config.max_delay
            )
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter = random.uniform(0.1, 0.3) * base_delay
            base_delay += jitter
        
        return base_delay
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if an exception should trigger a retry.
        
        Args:
            exception: The exception that occurred
            attempt: Current attempt number (0-based)
            
        Returns:
            bool: True if should retry
        """
        # Check circuit breaker
        if self._circuit_open:
            if time.time() - self._last_failure_time > self._circuit_timeout:
                self._circuit_open = False
                logger.info("Circuit breaker reset after timeout")
            else:
                return False
        
        # Check max retries
        if attempt >= self.config.max_retries:
            return False
        
        # Check exception type
        if isinstance(exception, AdoRateLimitError):
            return True
        
        if isinstance(exception, (AdoNetworkError, requests.exceptions.RequestException)):
            # Don't retry certain HTTP errors
            if hasattr(exception, 'response') and exception.response is not None:
                status_code = exception.response.status_code
                # Don't retry client errors (4xx) except rate limiting
                if 400 <= status_code < 500 and status_code != 429:
                    return False
            # Also check original exception if this is wrapped
            if isinstance(exception, AdoNetworkError) and hasattr(exception, 'original_exception'):
                orig = exception.original_exception
                if hasattr(orig, 'response') and orig.response is not None:
                    status_code = orig.response.status_code
                    # Don't retry client errors (4xx) except rate limiting
                    if 400 <= status_code < 500 and status_code != 429:
                        return False
            return True
        
        if isinstance(exception, (AdoTimeoutError, requests.exceptions.Timeout)):
            return True
        
        return False
    
    def _handle_failure(self, exception: Exception):
        """
        Handle failure tracking for circuit breaker.
        
        Args:
            exception: The exception that occurred
        """
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        # Open circuit breaker after many failures
        if self._failure_count >= 5:
            self._circuit_open = True
            logger.warning(f"Circuit breaker opened after {self._failure_count} failures")
    
    def _handle_success(self):
        """Handle successful request for circuit breaker."""
        if self._failure_count > 0:
            logger.info(f"Request succeeded after {self._failure_count} failures")
        
        self._failure_count = 0
        self._circuit_open = False
    
    def retry_on_failure(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator that adds retry logic to a function.
        
        Args:
            func: Function to wrap with retry logic
            
        Returns:
            Callable: Wrapped function with retry logic
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(self.config.max_retries + 1):
                try:
                    with tracer.start_as_current_span("retry_attempt") as span:
                        span.set_attribute("retry.attempt", attempt)
                        span.set_attribute("retry.max_retries", self.config.max_retries)
                        
                        result = func(*args, **kwargs)
                        
                        if attempt > 0:
                            span.set_attribute("retry.success_after_retries", True)
                        
                        self._handle_success()
                        return result
                        
                except Exception as e:
                    last_exception = e
                    
                    # Handle rate limiting specially
                    if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
                        retry_after = None
                        if hasattr(e.response, 'headers'):
                            retry_after = e.response.headers.get('Retry-After')
                            if retry_after:
                                try:
                                    retry_after = int(retry_after)
                                except ValueError:
                                    retry_after = None
                        
                        last_exception = AdoRateLimitError(
                            f"Rate limit exceeded on attempt {attempt + 1}",
                            retry_after=retry_after,
                            context={"attempt": attempt + 1, "url": str(e.response.url)},
                            original_exception=e
                        )
                    
                    # Handle network errors
                    elif isinstance(e, requests.exceptions.RequestException):
                        # For HTTPError, check if it's a non-retryable error
                        if isinstance(e, requests.exceptions.HTTPError) and hasattr(e, 'response') and e.response is not None:
                            status_code = e.response.status_code
                            # Don't wrap 4xx errors (except 429) - let them through as-is
                            if 400 <= status_code < 500 and status_code != 429:
                                last_exception = e
                            else:
                                last_exception = AdoNetworkError(
                                    f"Network error on attempt {attempt + 1}: {str(e)}",
                                    context={"attempt": attempt + 1, "error_type": type(e).__name__},
                                    original_exception=e
                                )
                        else:
                            last_exception = AdoNetworkError(
                                f"Network error on attempt {attempt + 1}: {str(e)}",
                                context={"attempt": attempt + 1, "error_type": type(e).__name__},
                                original_exception=e
                            )
                    
                    # Handle timeouts
                    elif isinstance(e, requests.exceptions.Timeout):
                        last_exception = AdoTimeoutError(
                            f"Request timeout on attempt {attempt + 1}",
                            context={"attempt": attempt + 1},
                            original_exception=e
                        )
                    
                    # Check if we should retry
                    if not self._should_retry(last_exception, attempt):
                        self._handle_failure(last_exception)
                        break
                    
                    # Calculate delay
                    retry_after = None
                    if isinstance(last_exception, AdoRateLimitError):
                        retry_after = last_exception.retry_after
                    
                    delay = self._calculate_delay(attempt, retry_after)
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {str(last_exception)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    with tracer.start_as_current_span("retry_delay") as span:
                        span.set_attribute("retry.delay_seconds", delay)
                        span.set_attribute("retry.attempt", attempt)
                        time.sleep(delay)
            
            # All retries exhausted
            self._handle_failure(last_exception)
            logger.error(f"All {self.config.max_retries + 1} attempts failed")
            raise last_exception
        
        return wrapper


def with_retry(config: RetryConfig):
    """
    Decorator factory for adding retry logic to functions.
    
    Args:
        config: Retry configuration
        
    Returns:
        Decorator function
    """
    retry_manager = RetryManager(config)
    return retry_manager.retry_on_failure


def create_retry_session(config: RetryConfig) -> requests.Session:
    """
    Create a requests Session with retry logic built-in.
    
    Args:
        config: Retry configuration
        
    Returns:
        requests.Session: Session with retry logic
    """
    session = requests.Session()
    retry_manager = RetryManager(config)
    
    # Wrap session methods with retry logic
    original_request = session.request
    session.request = retry_manager.retry_on_failure(original_request)
    
    return session