"""
Token estimation utilities for Azure DevOps MCP server.

This module provides token counting and response size estimation capabilities
to prevent context overflow when returning suggestions to LLMs.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Token estimation constants
CHARS_PER_TOKEN_ESTIMATE = 4  # Rough estimate for English text
MAX_RESPONSE_TOKENS = 1000  # Maximum tokens to allow in suggestion responses
SUGGESTION_BASE_TOKENS = 50  # Base tokens per suggestion (name, id, similarity)
ERROR_MESSAGE_BASE_TOKENS = 20  # Base tokens for error message text
ESTIMATION_FAILED = -1  # Sentinel value to indicate token estimation failure


class TokenEstimator:
    """
    Utility class for estimating token usage in API responses.

    Provides methods to estimate token consumption and limit response sizes
    to prevent context overflow for LLMs.
    """

    def __init__(self, max_response_tokens: int = MAX_RESPONSE_TOKENS):
        """
        Initialize the token estimator.

        Args:
            max_response_tokens: Maximum allowed tokens in a response
        """
        self.max_response_tokens = max_response_tokens

    def estimate_text_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.

        Uses a simple character-based estimation method that's reasonably
        accurate for English text and JSON structures.

        Args:
            text: Input text to estimate tokens for

        Returns:
            Estimated number of tokens
        """
        if not text:
            return 0

        # Remove extra whitespace and normalize
        normalized_text = re.sub(r"\s+", " ", text.strip())

        # Estimate tokens based on character count
        char_count = len(normalized_text)
        estimated_tokens = max(1, char_count // CHARS_PER_TOKEN_ESTIMATE)

        return estimated_tokens

    def estimate_json_tokens(self, data: Any) -> int:
        """
        Estimate the number of tokens in a JSON structure.

        Args:
            data: Data structure to be serialized to JSON

        Returns:
            Estimated number of tokens, or ESTIMATION_FAILED (-1) if serialization fails
        """
        if data is None:
            return 0

        try:
            json_text = json.dumps(data, separators=(",", ":"))
            return self.estimate_text_tokens(json_text)
        except (TypeError, ValueError) as e:
            logger.error(
                f"Failed to serialize data for token estimation: {e}. Data type: {type(data)}"
            )
            return ESTIMATION_FAILED

    def estimate_suggestion_tokens(self, suggestions: list[dict[str, Any]]) -> int:
        """
        Estimate the total tokens for a list of suggestions.

        Args:
            suggestions: List of suggestion dictionaries

        Returns:
            Estimated total tokens for all suggestions, or ESTIMATION_FAILED (-1) if input is invalid
        """
        if suggestions is None:
            logger.error("Cannot estimate tokens for None suggestions list")
            return ESTIMATION_FAILED

        if not suggestions:
            return 0

        if not isinstance(suggestions, list):
            logger.error(f"Expected list of suggestions, got {type(suggestions)}")
            return ESTIMATION_FAILED

        total_tokens = 0

        for i, suggestion in enumerate(suggestions):
            if not isinstance(suggestion, dict):
                logger.error(f"Suggestion at index {i} is not a dictionary: {type(suggestion)}")
                return ESTIMATION_FAILED
            # Base tokens for structure (name, id, similarity fields)
            suggestion_tokens = SUGGESTION_BASE_TOKENS

            # Add tokens for actual content
            name = suggestion.get("name", "")
            suggestion_tokens += self.estimate_text_tokens(name)

            # ID field if present
            if "id" in suggestion:
                suggestion_tokens += self.estimate_text_tokens(str(suggestion["id"]))

            total_tokens += suggestion_tokens

        return total_tokens

    def estimate_error_response_tokens(
        self, error_message: str, suggestions: list[dict[str, Any]]
    ) -> int:
        """
        Estimate total tokens for an error response with suggestions.

        Args:
            error_message: The error message text
            suggestions: List of suggestion dictionaries

        Returns:
            Estimated total tokens for the complete error response
        """
        # Base structure tokens (success: false, error field, suggestions field)
        base_tokens = ERROR_MESSAGE_BASE_TOKENS

        # Error message tokens
        message_tokens = self.estimate_text_tokens(error_message)

        # Suggestions tokens
        suggestion_tokens = self.estimate_suggestion_tokens(suggestions)

        return base_tokens + message_tokens + suggestion_tokens

    def limit_suggestions_by_tokens(
        self,
        suggestions: list[dict[str, Any]],
        error_message: str = "",
        max_suggestions: int = None,
    ) -> list[dict[str, Any]]:
        """
        Limit suggestions list to stay within token budget.

        Args:
            suggestions: Original list of suggestions
            error_message: Error message that will accompany suggestions
            max_suggestions: Maximum number of suggestions to consider (None for no limit)

        Returns:
            Truncated list of suggestions that fits within token budget
        """
        if not suggestions:
            return suggestions

        # Start with all suggestions or max_suggestions limit
        if max_suggestions is not None:
            limited_suggestions = suggestions[:max_suggestions]
        else:
            limited_suggestions = suggestions[:]

        # Check if we're within token budget
        while limited_suggestions:
            estimated_tokens = self.estimate_error_response_tokens(
                error_message, limited_suggestions
            )

            if estimated_tokens <= self.max_response_tokens:
                break

            # Remove the last suggestion and try again
            limited_suggestions = limited_suggestions[:-1]

        logger.info(
            f"Token limiting: {len(suggestions)} -> {len(limited_suggestions)} suggestions, "
            f"estimated tokens: {self.estimate_error_response_tokens(error_message, limited_suggestions)}"
        )

        return limited_suggestions

    def should_truncate_suggestions(
        self, suggestions: list[dict[str, Any]], error_message: str = ""
    ) -> bool:
        """
        Check if suggestions list should be truncated due to token limits.

        Args:
            suggestions: List of suggestions to check
            error_message: Error message that will accompany suggestions

        Returns:
            True if suggestions should be truncated, False otherwise
        """
        estimated_tokens = self.estimate_error_response_tokens(error_message, suggestions)
        return estimated_tokens > self.max_response_tokens

    def format_truncation_message(
        self, original_count: int, truncated_count: int, resource_type: str = "matches"
    ) -> str:
        """
        Create a message indicating that results were truncated.

        Args:
            original_count: Original number of matches
            truncated_count: Number of matches after truncation
            resource_type: Type of resource (for message formatting)

        Returns:
            Formatted truncation message
        """
        remaining = original_count - truncated_count
        if remaining <= 0:
            return ""

        return f"({remaining} more {resource_type} available)"


# Global instance for convenience
default_estimator = TokenEstimator()


def estimate_tokens(text: str) -> int:
    """
    Convenience function to estimate tokens in text using default estimator.

    Args:
        text: Input text to estimate tokens for

    Returns:
        Estimated number of tokens
    """
    return default_estimator.estimate_text_tokens(text)


def limit_suggestions_by_tokens(
    suggestions: list[dict[str, Any]],
    error_message: str = "",
    max_tokens: int = MAX_RESPONSE_TOKENS,
) -> list[dict[str, Any]]:
    """
    Convenience function to limit suggestions by token count.

    Args:
        suggestions: List of suggestion dictionaries
        error_message: Error message text
        max_tokens: Maximum allowed tokens

    Returns:
        Token-limited list of suggestions
    """
    estimator = TokenEstimator(max_tokens)
    return estimator.limit_suggestions_by_tokens(suggestions, error_message)
