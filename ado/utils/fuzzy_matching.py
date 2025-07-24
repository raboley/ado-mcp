"""
Fuzzy matching utilities for Azure DevOps MCP server.

This module provides intelligent string matching capabilities using Levenshtein distance
and weighted scoring to help LLMs find resources even with typos or slight naming differences.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, TypeVar

from Levenshtein import distance as levenshtein_distance

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Constants for weighted scoring
# These weights are optimized for Azure DevOps resource name matching patterns:

EXACT_SUBSTRING_WEIGHT = 1.0  # Perfect match - user typed exact substring
# E.g., "build" matches "CI-Build-Pipeline"

CASE_INSENSITIVE_WEIGHT = 0.9  # Very high confidence - only case differs
# E.g., "Build" matches "build" in "ci-build-test"

COMMON_WORD_WEIGHT = 0.8  # High confidence - shared meaningful words
# E.g., "test deploy" matches "Deploy-Test-Pipeline"

CHARACTER_DISTANCE_WEIGHT = 0.7  # Medium confidence - based on edit distance
# E.g., "buld" matches "build" (1 char typo)

DEFAULT_SIMILARITY_THRESHOLD = 0.5  # Minimum confidence for suggestions
# Tuned to balance helpful suggestions vs noise


@dataclass
class MatchResult:
    """
    Represents a fuzzy match result with similarity scoring.

    Attributes:
        item: The original item that was matched
        name: The display name used for matching
        id: The ID of the matched item (if available)
        similarity: Similarity score between 0.0 and 1.0
        match_type: Type of match found (exact, case_insensitive, fuzzy, etc.)
    """

    item: Any
    name: str
    id: str | None = None
    similarity: float = 0.0
    match_type: str = "fuzzy"


class FuzzyMatcher:
    """
    Advanced fuzzy matching engine using Levenshtein distance with weighted scoring.

    Provides intelligent string matching for Azure DevOps resources like pipelines,
    projects, and work items to help LLMs succeed even with minor typos or formatting differences.
    """

    def __init__(
        self,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        max_suggestions: int = 10,
        performance_threshold_ms: int = 200,
        exact_substring_weight: float = EXACT_SUBSTRING_WEIGHT,
        case_insensitive_weight: float = CASE_INSENSITIVE_WEIGHT,
        character_distance_weight: float = CHARACTER_DISTANCE_WEIGHT,
        common_word_weight: float = COMMON_WORD_WEIGHT,
    ):
        """
        Initialize the fuzzy matcher.

        Args:
            similarity_threshold: Minimum similarity score to include in results (0.0-1.0)
            max_suggestions: Maximum number of suggestions to return
            performance_threshold_ms: Maximum time allowed for matching operation
            exact_substring_weight: Weight for exact substring matches (default 1.0)
            case_insensitive_weight: Weight for case-insensitive matches (default 0.9)
            character_distance_weight: Weight for character distance-based matches (default 0.7)
            common_word_weight: Weight for common word matches (default 0.8)
        """
        self.similarity_threshold = similarity_threshold
        self.max_suggestions = max_suggestions
        self.performance_threshold_ms = performance_threshold_ms

        # Configurable matching weights
        self.exact_substring_weight = exact_substring_weight
        self.case_insensitive_weight = case_insensitive_weight
        self.character_distance_weight = character_distance_weight
        self.common_word_weight = common_word_weight

    def find_matches(
        self,
        query: str,
        candidates: list[T],
        name_extractor: callable = lambda x: str(x),
        id_extractor: callable = lambda x: getattr(x, "id", None),
    ) -> list[MatchResult]:
        """
        Find fuzzy matches for a query string against a list of candidates.

        Args:
            query: The search query string
            candidates: List of candidate items to match against
            name_extractor: Function to extract display name from candidate items
            id_extractor: Function to extract ID from candidate items

        Returns:
            List of MatchResult objects sorted by similarity score (descending)
        """
        start_time = time.time()

        if not query or not candidates:
            return []

        query_normalized = query.strip()
        if not query_normalized:
            return []

        results = []

        for candidate in candidates:
            try:
                candidate_name = name_extractor(candidate)
                if not candidate_name:
                    continue

                similarity = self._calculate_similarity(query_normalized, candidate_name)

                if similarity >= self.similarity_threshold:
                    match_type = self._determine_match_type(query_normalized, candidate_name)
                    candidate_id = id_extractor(candidate)

                    results.append(
                        MatchResult(
                            item=candidate,
                            name=candidate_name,
                            id=str(candidate_id) if candidate_id is not None else None,
                            similarity=similarity,
                            match_type=match_type,
                        )
                    )

            except Exception as e:
                logger.warning(f"Error processing candidate {candidate}: {e}")
                continue

        # Sort by similarity score (descending) and limit results
        results.sort(key=lambda x: x.similarity, reverse=True)
        results = results[: self.max_suggestions]

        # Log performance metrics
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Fuzzy matching completed: query='{query}', candidates={len(candidates)}, "
            f"matches={len(results)}, elapsed={elapsed_ms:.1f}ms"
        )

        if elapsed_ms > self.performance_threshold_ms:
            logger.warning(
                f"Fuzzy matching exceeded performance threshold: {elapsed_ms:.1f}ms > "
                f"{self.performance_threshold_ms}ms for {len(candidates)} candidates"
            )

        return results

    def _calculate_similarity(self, query: str, candidate: str) -> float:
        """
        Calculate similarity score using weighted criteria.

        Args:
            query: The search query string
            candidate: The candidate string to compare against

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Exact substring match (highest priority)
        if query in candidate:
            return self.exact_substring_weight

        # Case-insensitive exact substring match (high priority)
        query_lower = query.lower()
        candidate_lower = candidate.lower()
        if query_lower in candidate_lower:
            return self.case_insensitive_weight

        # Levenshtein distance-based similarity (medium priority)
        max_length = max(len(query), len(candidate))
        if max_length == 0:
            return 1.0

        distance = levenshtein_distance(query_lower, candidate_lower)
        char_similarity = (max_length - distance) / max_length
        char_score = char_similarity * self.character_distance_weight

        # Common word detection (medium priority)
        word_score = self._calculate_word_similarity(query_lower, candidate_lower)

        # Return the highest score from different matching strategies
        return max(char_score, word_score)

    def _calculate_word_similarity(self, query: str, candidate: str) -> float:
        """
        Calculate similarity based on common words and tokens.

        Args:
            query: The search query string (lowercase)
            candidate: The candidate string (lowercase)

        Returns:
            Word-based similarity score between 0.0 and 1.0
        """
        # Split on common separators
        query_words = set(self._tokenize(query))
        candidate_words = set(self._tokenize(candidate))

        if not query_words or not candidate_words:
            return 0.0

        # Calculate Jaccard similarity (intersection over union)
        intersection = len(query_words.intersection(candidate_words))
        union = len(query_words.union(candidate_words))

        if union == 0:
            return 0.0

        jaccard_similarity = intersection / union
        return jaccard_similarity * self.common_word_weight

    def _tokenize(self, text: str) -> list[str]:
        """
        Split text into tokens using common separators.

        Args:
            text: Input text to tokenize

        Returns:
            List of normalized tokens
        """
        # Common separators in Azure DevOps naming
        separators = [" ", "-", "_", ".", "/", "\\", "(", ")", "[", "]"]

        tokens = [text]
        for sep in separators:
            new_tokens = []
            for token in tokens:
                new_tokens.extend(token.split(sep))
            tokens = new_tokens

        # Filter out empty tokens and normalize
        return [token.strip().lower() for token in tokens if token.strip()]

    def _determine_match_type(self, query: str, candidate: str) -> str:
        """
        Determine the type of match found for logging and debugging.

        Args:
            query: The search query string
            candidate: The matched candidate string

        Returns:
            String describing the match type
        """
        if query == candidate:
            return "exact"
        elif query in candidate:
            return "exact_substring"
        elif query.lower() in candidate.lower():
            return "case_insensitive"
        elif self._calculate_word_similarity(query.lower(), candidate.lower()) > 0.5:
            return "word_match"
        else:
            return "fuzzy"


def create_suggestion_error_message(
    query: str, resource_type: str, matches: list[MatchResult], max_suggestions: int = 5
) -> str:
    """
    Create a user-friendly error message with fuzzy match suggestions.

    Args:
        query: The original search query that failed
        resource_type: Type of resource being searched (e.g., "Pipeline", "Project")
        matches: List of fuzzy match results
        max_suggestions: Maximum number of suggestions to include in error message

    Returns:
        Formatted error message string with suggestions
    """
    if not matches:
        return (
            f"{resource_type} '{query}' not found. No similar {resource_type.lower()}s available."
        )

    # Limit suggestions for readability
    suggestions = matches[:max_suggestions]
    suggestion_names = [f"'{match.name}'" for match in suggestions]

    if len(suggestion_names) == 1:
        suggestion_text = suggestion_names[0]
    elif len(suggestion_names) == 2:
        suggestion_text = f"{suggestion_names[0]} or {suggestion_names[1]}"
    else:
        suggestion_text = f"{', '.join(suggestion_names[:-1])}, or {suggestion_names[-1]}"

    base_message = f"{resource_type} '{query}' not found."

    if len(matches) > max_suggestions:
        return f"{base_message} Did you mean: {suggestion_text}? ({len(matches) - max_suggestions} more matches available)"
    else:
        return f"{base_message} Did you mean: {suggestion_text}?"


def extract_suggestions_for_response(
    matches: list[MatchResult], max_suggestions: int = 10
) -> list[dict[str, Any]]:
    """
    Extract suggestion data for API responses.

    Args:
        matches: List of fuzzy match results
        max_suggestions: Maximum number of suggestions to return

    Returns:
        List of dictionaries with suggestion data
    """
    suggestions = []

    for match in matches[:max_suggestions]:
        suggestion = {
            "name": match.name,
            "similarity": round(match.similarity, 3),
            "match_type": match.match_type,
        }

        if match.id is not None:
            suggestion["id"] = match.id

        suggestions.append(suggestion)

    return suggestions
