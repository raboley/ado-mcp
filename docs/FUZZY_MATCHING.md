# Fuzzy Matching Engine Documentation

This document explains the fuzzy matching implementation in the Azure DevOps MCP server, which helps LLMs find resources even with typos or slight naming differences.

## Overview

The fuzzy matching engine uses a sophisticated multi-layered approach combining exact matching, case-insensitive matching, Levenshtein distance calculations, and word-based similarity to provide intelligent suggestions when exact matches fail.

## Core Components

### FuzzyMatcher Class

The main `FuzzyMatcher` class provides the core matching functionality with configurable thresholds and performance requirements.

```python
from ado.utils.fuzzy_matching import FuzzyMatcher

# Basic usage
matcher = FuzzyMatcher(
    similarity_threshold=0.6,    # Minimum similarity score (0.0-1.0)
    max_suggestions=10,          # Maximum suggestions to return
    performance_threshold_ms=200 # Performance warning threshold
)

# Find matches
matches = matcher.find_matches(
    query="CI-Pipeline",
    candidates=pipeline_list,
    name_extractor=lambda p: p.name,
    id_extractor=lambda p: p.id
)
```

### Match Results

Each match result contains:

```python
@dataclass
class MatchResult:
    item: Any          # Original matched item
    name: str          # Display name used for matching
    id: Optional[str]  # ID of the matched item
    similarity: float  # Similarity score (0.0-1.0)
    match_type: str    # Type of match found
```

## Matching Algorithm

### Weighted Scoring System

The fuzzy matcher uses a weighted scoring system with the following priorities:

1. **Exact Match** (weight: 1.0)
   - Perfect string match
   - Returns similarity score of 1.0

2. **Case-Insensitive Exact Match** (weight: 0.9)
   - Case-insensitive perfect match
   - Returns similarity score of 0.9

3. **Exact Substring Match** (weight: 1.0)
   - Query is found as substring in candidate
   - Returns similarity score of 1.0

4. **Case-Insensitive Substring Match** (weight: 0.9)
   - Query found as substring (case-insensitive)
   - Returns similarity score of 0.9

5. **Character Distance** (weight: 0.7)
   - Based on Levenshtein distance algorithm
   - Score = (max_length - distance) / max_length * 0.7

6. **Word Similarity** (weight: 0.8)
   - Based on Jaccard similarity of tokenized words
   - Handles different separators (-, _, ., /, \, etc.)

### Match Types

The system identifies different types of matches for debugging and analytics:

- `exact`: Perfect string match
- `exact_substring`: Query found as exact substring
- `case_insensitive`: Case-insensitive match
- `word_match`: High word-based similarity
- `fuzzy`: Levenshtein distance-based match

## Usage Examples

### Pipeline Matching

```python
from ado.utils.fuzzy_matching import FuzzyMatcher

# Mock pipeline data
pipelines = [
    {"name": "CI Pipeline", "id": "123"},
    {"name": "CI-Build-Pipeline", "id": "124"},
    {"name": "Frontend Deploy", "id": "125"}
]

matcher = FuzzyMatcher()

# Find matches for typo
matches = matcher.find_matches(
    "CI-Pipeline",  # User typed with dash
    pipelines,
    name_extractor=lambda p: p["name"],
    id_extractor=lambda p: p["id"]
)

# Results will include "CI Pipeline" with high similarity
print(f"Found {len(matches)} matches:")
for match in matches:
    print(f"  {match.name} (similarity: {match.similarity:.2f})")
```

### Project Discovery

```python
# Find projects with fuzzy matching
matches = matcher.find_matches(
    "ado mcp",  # Space instead of dash
    projects,
    name_extractor=lambda p: p.name
)

# Will match "ado-mcp" with high word similarity
```

### Custom Extractors

```python
# Use project description for matching
matches = matcher.find_matches(
    "Azure DevOps",
    projects,
    name_extractor=lambda p: p.description,
    id_extractor=lambda p: f"proj-{p.id}"
)
```

## Error Message Generation

### Creating User-Friendly Suggestions

```python
from ado.utils.fuzzy_matching import create_suggestion_error_message

# Generate error message with suggestions
error_msg = create_suggestion_error_message(
    query="CI-Pipe",
    resource_type="Pipeline", 
    matches=matches,
    max_suggestions=5
)

# Output: "Pipeline 'CI-Pipe' not found. Did you mean: 'CI Pipeline', 'CI-Build', 'CI-Deploy'?"
```

### API Response Format

```python
from ado.utils.fuzzy_matching import extract_suggestions_for_response

# Extract structured data for API responses
suggestions = extract_suggestions_for_response(matches, max_suggestions=10)

# Returns list of dictionaries:
# [
#   {
#     "name": "CI Pipeline",
#     "id": "123", 
#     "similarity": 0.950,
#     "match_type": "case_insensitive"
#   },
#   ...
# ]
```

## Performance Considerations

### Requirements

- **Target Performance**: <200ms for 100 items
- **Memory Usage**: Efficient for up to 1000 candidates
- **Scalability**: Linear time complexity O(n*m) where n=candidates, m=query length

### Performance Monitoring

The fuzzy matcher automatically logs performance metrics:

```
INFO: Fuzzy matching completed: query='CI-Pipeline', candidates=50, matches=3, elapsed=45.2ms
WARNING: Fuzzy matching exceeded performance threshold: 250.1ms > 200ms for 200 candidates
```

### Optimization Tips

1. **Pre-filter candidates** when possible to reduce search space
2. **Use appropriate similarity thresholds** (0.6-0.8 typically optimal)
3. **Limit max_suggestions** to reduce processing overhead
4. **Cache results** for frequently searched queries

## Integration with Token Estimation

The fuzzy matcher integrates with token estimation to prevent context overflow:

```python
from ado.utils.token_estimation import limit_suggestions_by_tokens

# Get fuzzy matches
matches = matcher.find_matches(query, candidates, name_extractor)

# Convert to suggestion format
suggestions = extract_suggestions_for_response(matches)

# Limit by token budget
limited_suggestions = limit_suggestions_by_tokens(
    suggestions,
    error_message="Pipeline 'xyz' not found",
    max_tokens=1000
)
```

## Configuration Guidelines

### Similarity Threshold Selection

- **0.5-0.6**: Very permissive, may include low-quality matches
- **0.6-0.7**: Balanced, good for general use (recommended)
- **0.7-0.8**: Conservative, high-quality matches only
- **0.8+**: Very strict, mostly exact or near-exact matches

### Max Suggestions

- **5-10**: Good for error messages and human consumption
- **10-20**: Suitable for API responses
- **20+**: May cause token overflow, use with token limiting

### Performance Thresholds

- **100ms**: Very fast, suitable for real-time applications
- **200ms**: Acceptable for most MCP operations (default)
- **500ms**: Slow, consider optimization
- **1000ms+**: Unacceptable, requires investigation

## Error Handling

### Graceful Degradation

The fuzzy matcher handles various error conditions gracefully:

- **Invalid candidates**: Skipped with warning logs
- **Empty names**: Ignored silently
- **Unicode issues**: Handled transparently
- **Memory constraints**: Automatic limiting via max_suggestions

### Logging Levels

- **INFO**: Normal operation metrics and results
- **WARNING**: Performance issues, invalid candidates
- **ERROR**: Critical failures (rare)

## Testing

### Unit Test Coverage

The fuzzy matching engine includes comprehensive test coverage:

- **Core functionality**: Exact, substring, and fuzzy matching
- **Performance requirements**: Sub-200ms for 100 items
- **Edge cases**: Unicode, empty inputs, large datasets
- **Error handling**: Invalid data, memory constraints

### Example Test

```python
def test_fuzzy_matching_with_typos():
    matcher = FuzzyMatcher()
    candidates = [MockPipeline(1, "CI Pipeline")]
    
    matches = matcher.find_matches(
        "CI-Pipeline",  # Typo: dash instead of space
        candidates,
        name_extractor=lambda p: p.name
    )
    
    assert len(matches) > 0
    assert matches[0].name == "CI Pipeline"
    assert matches[0].similarity >= 0.6
```

## Best Practices

### For LLM Integration

1. **Always provide suggestions** when exact matches fail
2. **Use descriptive error messages** with "Did you mean..." format
3. **Limit suggestions** to prevent context overflow
4. **Log operations** for analytics and debugging

### For Performance

1. **Profile with realistic data** sizes from your Azure DevOps organization
2. **Monitor response times** and adjust thresholds as needed
3. **Consider caching** for frequently accessed resources
4. **Precompute similarity** for static datasets when possible

### For User Experience

1. **Prioritize exact and substring matches** over fuzzy matches
2. **Include IDs in suggestions** for programmatic access
3. **Sort by similarity score** to show best matches first
4. **Provide fallback messaging** when no matches found

## Troubleshooting

### Common Issues

**Issue**: No matches found for obvious similarities
- **Cause**: Similarity threshold too high
- **Solution**: Lower threshold to 0.5-0.6

**Issue**: Too many low-quality matches
- **Cause**: Similarity threshold too low
- **Solution**: Raise threshold to 0.7-0.8

**Issue**: Slow performance
- **Cause**: Large candidate sets, complex names
- **Solution**: Pre-filter candidates, increase performance threshold warning

**Issue**: Context overflow in LLM responses
- **Cause**: Too many suggestions, long names
- **Solution**: Use token limiting, reduce max_suggestions

### Debug Mode

Enable verbose logging for troubleshooting:

```python
import logging
logging.getLogger('ado.utils.fuzzy_matching').setLevel(logging.DEBUG)
```

This will log detailed information about each matching operation, including similarity calculations and performance metrics.