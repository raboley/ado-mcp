"""
Unit tests for fuzzy matching utilities.

Tests cover the core fuzzy matching engine including Levenshtein distance,
weighted scoring, performance requirements, and edge cases.
"""

import pytest
import time
from dataclasses import dataclass
from typing import List

from ado.utils.fuzzy_matching import (
    FuzzyMatcher,
    MatchResult,
    create_suggestion_error_message,
    extract_suggestions_for_response,
    DEFAULT_SIMILARITY_THRESHOLD
)


@dataclass
class MockPipeline:
    """Mock pipeline object for testing."""
    id: int
    name: str


@dataclass
class MockProject:
    """Mock project object for testing."""
    id: str
    name: str
    description: str = ""


class TestFuzzyMatcher:
    """Test cases for the FuzzyMatcher class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = FuzzyMatcher()
        
        # Test data - realistic Azure DevOps pipeline names
        self.pipelines = [
            MockPipeline(1, "CI Pipeline"),
            MockPipeline(2, "CI-Build-Pipeline"),
            MockPipeline(3, "CI-Deploy"),
            MockPipeline(4, "Frontend Build"),
            MockPipeline(5, "Backend Deploy"),
            MockPipeline(6, "Integration Tests"),
            MockPipeline(7, "Release Pipeline"),
            MockPipeline(8, "Mobile App Build"),
            MockPipeline(9, "API Tests"),
            MockPipeline(10, "Database Migration")
        ]
        
        self.projects = [
            MockProject("proj-1", "ado-mcp", "Azure DevOps MCP Server"),
            MockProject("proj-2", "ado mcp", "Duplicate project name"),
            MockProject("proj-3", "web-app", "Main web application"),
            MockProject("proj-4", "mobile-app", "Mobile application"),
            MockProject("proj-5", "infrastructure", "Infrastructure as code")
        ]

    def test_exact_match_highest_priority(self):
        """Test that exact matches receive highest similarity scores."""
        matches = self.matcher.find_matches(
            "CI Pipeline",
            self.pipelines,
            name_extractor=lambda p: p.name
        )
        
        assert len(matches) > 0, "Should find at least one match for exact query"
        assert matches[0].name == "CI Pipeline", f"Expected 'CI Pipeline' but got '{matches[0].name}'"
        assert matches[0].similarity == 1.0, f"Expected similarity 1.0 but got {matches[0].similarity}"
        assert matches[0].match_type == "exact", f"Expected match_type 'exact' but got '{matches[0].match_type}'"

    def test_case_insensitive_matching(self):
        """Test that case-insensitive matches work correctly."""
        matches = self.matcher.find_matches(
            "ci pipeline",
            self.pipelines,
            name_extractor=lambda p: p.name
        )
        
        assert len(matches) > 0, "Should find matches for case-insensitive query"
        ci_pipeline_match = next((m for m in matches if m.name == "CI Pipeline"), None)
        assert ci_pipeline_match is not None, "Should find 'CI Pipeline' for 'ci pipeline' query"
        assert ci_pipeline_match.similarity >= 0.8, f"Expected high similarity but got {ci_pipeline_match.similarity}"

    def test_substring_matching(self):
        """Test that substring matches are found and scored appropriately."""
        matches = self.matcher.find_matches(
            "Build",
            self.pipelines,
            name_extractor=lambda p: p.name
        )
        
        build_matches = [m for m in matches if "Build" in m.name]
        assert len(build_matches) >= 2, f"Expected at least 2 build matches but got {len(build_matches)}"
        
        # Check that all build matches have high similarity
        for match in build_matches:
            assert match.similarity >= 0.8, f"Expected high similarity for '{match.name}' but got {match.similarity}"

    def test_fuzzy_matching_with_typos(self):
        """Test that fuzzy matching handles common typos."""
        # Test with typo: "CI-Pipeline" vs "CI Pipeline" 
        matches = self.matcher.find_matches(
            "CI-Pipeline",
            self.pipelines,
            name_extractor=lambda p: p.name
        )
        
        ci_pipeline_match = next((m for m in matches if m.name == "CI Pipeline"), None)
        assert ci_pipeline_match is not None, "Should find 'CI Pipeline' for 'CI-Pipeline' query with typo"
        assert ci_pipeline_match.similarity >= 0.6, f"Expected similarity >= 0.6 but got {ci_pipeline_match.similarity}"

    def test_pipeline_name_variations_comprehensive(self):
        """Test comprehensive pipeline name variations that LLMs might use."""
        # Common variations LLMs might try
        test_cases = [
            ("ci pipeline", "CI Pipeline"),           # case difference
            ("CI-Pipeline", "CI Pipeline"),           # dash vs space  
            ("ci_pipeline", "CI Pipeline"),           # underscore vs space
            ("cipipeline", "CI Pipeline"),            # missing space/separator
            ("CI Pipline", "CI Pipeline"),            # typo in "Pipeline"
            ("build", "Frontend Build"),              # partial match
            ("deploy", "Backend Deploy"),             # partial match
            ("integration", "Integration Tests"),      # partial match
        ]
        
        for query, expected_match in test_cases:
            matches = self.matcher.find_matches(
                query,
                self.pipelines,
                name_extractor=lambda p: p.name
            )
            
            found_expected = any(m.name == expected_match for m in matches)
            assert found_expected, f"Query '{query}' should find '{expected_match}' but matches were: {[m.name for m in matches]}"

    def test_similarity_threshold_filtering(self):
        """Test that results below similarity threshold are filtered out."""
        # Use high threshold to filter out weak matches
        strict_matcher = FuzzyMatcher(similarity_threshold=0.8)
        
        matches = strict_matcher.find_matches(
            "xyz",  # Very different query
            self.pipelines,
            name_extractor=lambda p: p.name
        )
        
        assert len(matches) == 0, f"Expected no matches for very different query but got {len(matches)}"

    def test_max_suggestions_limiting(self):
        """Test that results are limited to max_suggestions."""
        limited_matcher = FuzzyMatcher(max_suggestions=3)
        
        matches = limited_matcher.find_matches(
            "i",  # Should match many pipelines
            self.pipelines,
            name_extractor=lambda p: p.name
        )
        
        assert len(matches) <= 3, f"Expected at most 3 matches but got {len(matches)}"

    def test_results_sorted_by_similarity(self):
        """Test that results are sorted by similarity score in descending order."""
        matches = self.matcher.find_matches(
            "CI",
            self.pipelines,
            name_extractor=lambda p: p.name
        )
        
        assert len(matches) >= 2, "Should find multiple matches for 'CI' query"
        
        # Check that similarities are in descending order
        for i in range(len(matches) - 1):
            assert matches[i].similarity >= matches[i + 1].similarity, \
                f"Results not sorted: {matches[i].similarity} < {matches[i + 1].similarity}"

    def test_id_extraction(self):
        """Test that IDs are correctly extracted from candidate items."""
        matches = self.matcher.find_matches(
            "CI Pipeline",
            self.pipelines,
            name_extractor=lambda p: p.name,
            id_extractor=lambda p: p.id
        )
        
        assert len(matches) > 0, "Should find matches"
        ci_match = next((m for m in matches if m.name == "CI Pipeline"), None)
        assert ci_match is not None, "Should find CI Pipeline match"
        assert ci_match.id == "1", f"Expected ID '1' but got '{ci_match.id}'"

    def test_empty_query_handling(self):
        """Test handling of empty or whitespace-only queries."""
        test_queries = ["", "   ", "\t", "\n"]
        
        for query in test_queries:
            matches = self.matcher.find_matches(
                query,
                self.pipelines,
                name_extractor=lambda p: p.name
            )
            assert len(matches) == 0, f"Expected no matches for empty query '{repr(query)}' but got {len(matches)}"

    def test_empty_candidates_handling(self):
        """Test handling of empty candidate lists."""
        matches = self.matcher.find_matches(
            "test query",
            [],
            name_extractor=lambda p: p.name
        )
        
        assert len(matches) == 0, "Expected no matches for empty candidates list"

    def test_performance_requirement(self):
        """Test that fuzzy matching meets performance requirements (<200ms for 100 items)."""
        # Create 100 test items
        large_pipelines = [
            MockPipeline(i, f"Pipeline-{i:03d}-Build-Deploy-Test")
            for i in range(100)
        ]
        
        start_time = time.time()
        matches = self.matcher.find_matches(
            "Pipeline-050",
            large_pipelines,
            name_extractor=lambda p: p.name
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert elapsed_ms < 200, f"Performance requirement violated: {elapsed_ms:.1f}ms > 200ms for 100 items"
        assert len(matches) > 0, "Should find matches in performance test"

    def test_word_similarity_matching(self):
        """Test word-based similarity matching for different separators."""
        # Test with different separator styles
        test_cases = [
            ("ado_mcp", "ado-mcp"),
            ("ado.mcp", "ado mcp"),
            ("web app", "web-app"),
            ("mobile/app", "mobile-app")
        ]
        
        for query, candidate_name in test_cases:
            candidates = [MockProject("test", candidate_name)]
            matches = self.matcher.find_matches(
                query,
                candidates,
                name_extractor=lambda p: p.name
            )
            
            assert len(matches) > 0, f"Should find match for '{query}' -> '{candidate_name}'"
            assert matches[0].similarity >= 0.6, \
                f"Expected similarity >= 0.6 for '{query}' -> '{candidate_name}' but got {matches[0].similarity}"

    def test_error_handling_for_invalid_candidates(self):
        """Test that invalid candidates are handled gracefully."""
        # Mix valid and invalid candidates
        mixed_candidates = [
            MockPipeline(1, "Valid Pipeline"),
            None,  # Invalid candidate
            MockPipeline(2, ""),  # Empty name
            MockPipeline(3, "Another Valid Pipeline")
        ]
        
        matches = self.matcher.find_matches(
            "Valid",
            mixed_candidates,
            name_extractor=lambda p: p.name if p else None
        )
        
        # Should find valid matches despite invalid candidates
        valid_matches = [m for m in matches if "Valid" in m.name]
        assert len(valid_matches) == 2, f"Expected 2 valid matches but got {len(valid_matches)}"

    def test_llm_typical_error_scenarios(self):
        """Test scenarios typical of LLM pipeline name errors."""
        # Common LLM mistakes when calling pipeline tools
        llm_errors = [
            ("Build Pipeline", "CI-Build-Pipeline"),     # Generic to specific (more logical match)
            ("deploy", "Backend Deploy"),                # Lowercase partial
            ("ci-build", "CI-Build-Pipeline"),          # Partial with dash
            ("release", "Release Pipeline"),             # Single word
            ("mobile build", "Mobile App Build"),        # Missing word (need lower threshold)
        ]
        
        for llm_query, expected_pipeline in llm_errors:
            matches = self.matcher.find_matches(
                llm_query,
                self.pipelines,
                name_extractor=lambda p: p.name
            )
            
            found_expected = any(m.name == expected_pipeline for m in matches)
            best_match = matches[0].name if matches else "No matches"
            
            assert found_expected, (
                f"LLM query '{llm_query}' should find '{expected_pipeline}' "
                f"but best match was '{best_match}'. All matches: {[m.name for m in matches]}"
            )


class TestSuggestionUtilities:
    """Test cases for suggestion utility functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_matches = [
            MatchResult(
                item=MockPipeline(1, "CI Pipeline"),
                name="CI Pipeline", 
                id="1",
                similarity=0.95,
                match_type="exact"
            ),
            MatchResult(
                item=MockPipeline(2, "CI-Build"), 
                name="CI-Build",
                id="2", 
                similarity=0.80,
                match_type="fuzzy"
            ),
            MatchResult(
                item=MockPipeline(3, "Build Pipeline"),
                name="Build Pipeline",
                id="3",
                similarity=0.70,
                match_type="word_match"
            )
        ]

    def test_create_suggestion_error_message_single_suggestion(self):
        """Test error message creation with single suggestion."""
        matches = self.sample_matches[:1]
        message = create_suggestion_error_message("CI-Pipe", "Pipeline", matches)
        
        expected_parts = ["Pipeline 'CI-Pipe' not found", "Did you mean: 'CI Pipeline'?"]
        for part in expected_parts:
            assert part in message, f"Expected '{part}' in message but got: {message}"

    def test_create_suggestion_error_message_multiple_suggestions(self):
        """Test error message creation with multiple suggestions."""
        message = create_suggestion_error_message("CI-Pipe", "Pipeline", self.sample_matches)
        
        expected_parts = [
            "Pipeline 'CI-Pipe' not found",
            "Did you mean:",
            "'CI Pipeline'",
            "'CI-Build'",
            "'Build Pipeline'"
        ]
        
        for part in expected_parts:
            assert part in message, f"Expected '{part}' in message but got: {message}"

    def test_create_suggestion_error_message_no_matches(self):
        """Test error message creation with no matches."""
        message = create_suggestion_error_message("nonexistent", "Pipeline", [])
        
        expected_message = "Pipeline 'nonexistent' not found. No similar pipelines available."
        assert message == expected_message, f"Expected specific no-matches message but got: {message}"

    def test_create_suggestion_error_message_truncation(self):
        """Test error message with truncation when too many suggestions."""
        # Create many matches
        many_matches = [
            MatchResult(
                item=MockPipeline(i, f"Pipeline-{i}"),
                name=f"Pipeline-{i}",
                id=str(i),
                similarity=0.8 - (i * 0.05),
                match_type="fuzzy"
            ) for i in range(10)
        ]
        
        message = create_suggestion_error_message("Pipeline", "Pipeline", many_matches, max_suggestions=3)
        
        assert "7 more matches available" in message, f"Expected truncation message but got: {message}"

    def test_extract_suggestions_for_response(self):
        """Test extraction of suggestion data for API responses."""
        suggestions = extract_suggestions_for_response(self.sample_matches)
        
        assert len(suggestions) == 3, f"Expected 3 suggestions but got {len(suggestions)}"
        
        # Check first suggestion structure
        first_suggestion = suggestions[0]
        expected_keys = {"name", "similarity", "match_type", "id"}
        assert set(first_suggestion.keys()) == expected_keys, \
            f"Expected keys {expected_keys} but got {set(first_suggestion.keys())}"
        
        assert first_suggestion["name"] == "CI Pipeline", \
            f"Expected name 'CI Pipeline' but got '{first_suggestion['name']}'"
        assert first_suggestion["id"] == "1", \
            f"Expected id '1' but got '{first_suggestion['id']}'"
        assert isinstance(first_suggestion["similarity"], float), \
            f"Expected similarity to be float but got {type(first_suggestion['similarity'])}"

    def test_extract_suggestions_respects_max_limit(self):
        """Test that suggestion extraction respects maximum limit."""
        suggestions = extract_suggestions_for_response(self.sample_matches, max_suggestions=2)
        
        assert len(suggestions) == 2, f"Expected 2 suggestions but got {len(suggestions)}"
        assert suggestions[0]["name"] == "CI Pipeline", "Should keep highest similarity match"
        assert suggestions[1]["name"] == "CI-Build", "Should keep second highest similarity match"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters."""
        matcher = FuzzyMatcher()
        
        unicode_pipelines = [
            MockPipeline(1, "Déployment Pipeline"),
            MockPipeline(2, "测试 Pipeline"),
            MockPipeline(3, "Pipeline (v2.0)")
        ]
        
        matches = matcher.find_matches(
            "Deployment",
            unicode_pipelines,
            name_extractor=lambda p: p.name
        )
        
        # Should handle Unicode gracefully without errors
        assert isinstance(matches, list), "Should return list even with Unicode characters"

    def test_very_long_strings(self):
        """Test handling of very long strings."""
        matcher = FuzzyMatcher()
        
        long_name = "Very " * 100 + "Long Pipeline Name"
        long_candidates = [MockPipeline(1, long_name)]
        
        matches = matcher.find_matches(
            "Very Long",
            long_candidates,
            name_extractor=lambda p: p.name
        )
        
        assert len(matches) > 0, "Should handle very long strings"
        assert matches[0].similarity > 0, "Should find similarity in very long strings"

    def test_custom_extractors(self):
        """Test custom name and ID extractors."""
        matcher = FuzzyMatcher()
        
        # Use project description as name for matching
        matches = matcher.find_matches(
            "Azure DevOps",
            [MockProject("proj-1", "ado-mcp", "Azure DevOps MCP Server")],
            name_extractor=lambda p: p.description,
            id_extractor=lambda p: f"project-{p.id}"
        )
        
        assert len(matches) > 0, "Should work with custom extractors"
        assert matches[0].name == "Azure DevOps MCP Server", \
            f"Expected description as name but got '{matches[0].name}'"
        assert matches[0].id == "project-proj-1", \
            f"Expected custom ID format but got '{matches[0].id}'"


class TestIntegrationWithLLMErrors:
    """Test integration scenarios specifically for LLM error cases."""

    def test_run_pipeline_name_errors(self):
        """Test common errors when LLMs try to run pipelines by name."""
        matcher = FuzzyMatcher()
        pipelines = [
            MockPipeline(123, "Main CI Pipeline"),
            MockPipeline(124, "Feature Branch CI"),
            MockPipeline(125, "Release Pipeline"),
            MockPipeline(126, "Hotfix Pipeline")
        ]
        
        # Common LLM errors when trying to run pipelines
        error_scenarios = [
            ("Main CI", "Main CI Pipeline"),              # Missing word
            ("main ci pipeline", "Main CI Pipeline"),     # Case issues
            ("MainCIPipeline", "Main CI Pipeline"),       # Missing spaces
            ("Main-CI-Pipeline", "Main CI Pipeline"),     # Wrong separators
            ("CI Pipeline", "Main CI Pipeline"),          # Partial match
            ("Feature CI", "Feature Branch CI"),          # Partial match
            ("release", "Release Pipeline"),               # Single word
        ]
        
        for error_query, expected_pipeline in error_scenarios:
            matches = matcher.find_matches(
                error_query,
                pipelines,
                name_extractor=lambda p: p.name,
                id_extractor=lambda p: p.id
            )
            
            # Should find the expected pipeline
            found_expected = any(m.name == expected_pipeline for m in matches)
            
            if not found_expected:
                match_names = [m.name for m in matches]
                pytest.fail(
                    f"LLM error scenario failed:\n"
                    f"  Query: '{error_query}'\n"
                    f"  Expected: '{expected_pipeline}'\n"  
                    f"  Found matches: {match_names}\n"
                    f"  Should have found expected pipeline in results"
                )

    def test_project_discovery_errors(self):
        """Test common errors when LLMs try to discover projects."""
        matcher = FuzzyMatcher()
        projects = [
            MockProject("proj-1", "web-application", "Main web app"),
            MockProject("proj-2", "mobile-ios", "iOS mobile app"),
            MockProject("proj-3", "api-service", "Backend API service"),
            MockProject("proj-4", "infrastructure-terraform", "Infrastructure code")
        ]
        
        # Common LLM project discovery errors
        discovery_scenarios = [
            ("mobile", "mobile-ios"),                     # Partial match
            ("api", "api-service"),                       # Partial match
            ("infrastructure", "infrastructure-terraform"), # Partial match
            ("web_application", "web-application"),        # Underscore vs dash
            ("mobileios", "mobile-ios"),                  # Missing separator
        ]
        
        for query, expected_project in discovery_scenarios:
            matches = matcher.find_matches(
                query,
                projects, 
                name_extractor=lambda p: p.name,
                id_extractor=lambda p: p.id
            )
            
            found_expected = any(m.name == expected_project for m in matches)
            
            assert found_expected, (
                f"Project discovery failed for '{query}' -> '{expected_project}'. "
                f"Found: {[m.name for m in matches]}"
            )