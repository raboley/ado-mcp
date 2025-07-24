# PRD: LLM-Friendly MCP Server Enhancement

## Introduction

This feature enhances the Azure DevOps MCP server to be more intuitive and efficient for LLM interactions. The primary problem is that LLMs currently require multiple tool calls when they make naming mistakes or need to discover available resources. For example, if an LLM tries to run a pipeline called "CI-Pipeline" but the actual name is "CI Pipeline", it gets an error and must make additional calls to list all pipelines and try again.

The goal is to make the MCP server anticipate LLM needs by providing intelligent error responses with contextual suggestions, reducing the total number of tool calls required to complete common tasks.

## Goals

- Reduce average tool calls per LLM session by 30-50%
- Eliminate the need for separate "list" calls after failed "find by name" operations
- Provide intelligent suggestions when exact matches fail
- Maintain backward compatibility while improving user experience
- Optimize the most common workflow: pipeline execution by name

## User Stories

**As an LLM assistant**, I want to run a pipeline by name with fuzzy matching, so that small typos or formatting differences don't require additional tool calls.

**As an LLM assistant**, I want to receive helpful suggestions when my queries fail, so that I can immediately retry with the correct information instead of making separate discovery calls.

**As an LLM assistant**, I want consolidated tools that handle both ID and name-based operations, so that I don't have to choose between multiple similar tools.

**As a developer using the MCP server**, I want existing tool signatures to remain stable, so that my current integrations continue working.

**As an LLM assistant**, I want token-aware response limiting, so that I receive manageable lists of suggestions without context overflow.

## Functional Requirements

### 1. Intelligent Pipeline Operations
1.1. The system must accept both pipeline IDs and names in a single `run_pipeline` tool
1.2. When a pipeline name doesn't match exactly, the system must return fuzzy matches using Levenshtein distance algorithm
1.3. The system must limit suggestions to prevent token overflow, using response size estimation
1.4. The system must provide traditional error responses with suggestions embedded in the error message
1.5. The system must prioritize recently used or commonly accessed pipelines in suggestions

### 2. Smart Project Discovery
2.1. The system must accept both project IDs and names in project-related tools
2.2. When project names fail to match, the system must return top 10 most likely matches
2.3. The system must use fuzzy string matching for typo tolerance (e.g., "ado-mcp" matches "ado mcp")
2.4. The system must include project descriptions in suggestions when available

### 3. Tool Consolidation
3.1. The system must replace existing separate ID/name tools with unified versions:
   - `run_pipeline` (replaces `run_pipeline_by_name` and ID-based calls)
   - `get_project` (handles both ID and name lookups)
   - `find_work_item` (consolidates work item discovery)
3.2. The system must maintain existing function signatures where possible for backward compatibility
3.3. The system must auto-detect whether input is an ID (numeric/UUID) or name (string)

### 4. Context-Aware Error Responses
4.1. When pipeline not found, the system must return error message with up to 10 similar pipeline names
4.2. When project not found, the system must return error message with up to 10 similar project names
4.3. The system must include usage hints in error messages (e.g., "Did you mean: 'CI-Pipeline', 'CI-Build', 'CI-Deploy'?")
4.4. The system must estimate response token size and truncate suggestions if needed

### 5. Fuzzy Matching Algorithm
5.1. The system must implement Levenshtein distance calculation for string similarity
5.2. The system must score matches with weighted criteria:
   - Exact substring match: highest priority
   - Case-insensitive match: high priority  
   - Character distance: medium priority
   - Common word detection: medium priority
5.3. The system must return matches with similarity scores above 60% threshold
5.4. The system must sort suggestions by similarity score descending

## Non-Goals

- Semantic matching using NLP/embeddings (future consideration)
- Real-time learning from LLM usage patterns (future consideration)
- Complete elimination of all existing tools (maintain stability)
- Support for partial pipeline execution or advanced workflow automation
- Integration with external fuzzy matching services

## Design Considerations

### Tool Response Format
```json
{
  "success": false,
  "error": "Pipeline 'CI-Pipeline' not found. Did you mean: 'CI Pipeline', 'CI-Build-Pipeline', 'CI-Deploy'?",
  "suggestions": [
    {"name": "CI Pipeline", "id": 123, "similarity": 0.85},
    {"name": "CI-Build-Pipeline", "id": 124, "similarity": 0.75},
    {"name": "CI-Deploy", "id": 125, "similarity": 0.65}
  ]
}
```

### Token Management
- Estimate each suggestion consumes ~50-100 tokens
- Limit total suggestion response to ~1000 tokens maximum
- Prioritize by similarity score when truncating

### UI/UX Considerations
- Error messages must be human-readable for debugging
- Suggestions must include both display names and IDs for flexibility
- Response format must remain JSON-serializable for MCP compatibility

## Technical Considerations

### Dependencies
- Existing Azure DevOps API client infrastructure
- Python `python-Levenshtein` library for fuzzy matching
- Current MCP server architecture and tool registration system

### Performance Requirements
- Fuzzy matching must complete within 200ms for lists up to 100 items
- Suggestion generation should not significantly impact existing tool response times
- Caching of project/pipeline lists recommended for frequently accessed organizations

### Integration Points
- Modify existing tool handlers in `ado/tools/` directory
- Update tool schemas to accept flexible input types (ID or name)
- Enhance error handling middleware to generate intelligent suggestions

## Success Metrics

### Primary Metrics
- **Reduced tool calls**: Average tool calls per LLM session decreases by 30-50%
- **Improved success rate**: Pipeline execution success rate on first attempt increases by 40%
- **Faster completion**: Time-to-completion for "run pipeline by name" workflow decreases by 60%

### Secondary Metrics  
- Error rate for pipeline name resolution decreases by 70%
- LLM retry attempts for failed operations decrease by 50%
- User satisfaction with tool responsiveness improves (qualitative feedback)

### Success Criteria
- LLM can successfully run any pipeline with minor name variations in 1-2 tool calls maximum
- Zero cases where LLM needs separate `list_pipelines` call after failed `run_pipeline` 
- Tool consolidation reduces total number of available tools by 20-30% while maintaining functionality

## Open Questions

### Technical Implementation
- Should we implement caching for fuzzy match results to improve performance?
- How should we handle very large organizations with 500+ pipelines (scaling concerns)?
- What's the optimal similarity threshold (currently proposed 60%)?

### User Experience
- Should suggestions include additional metadata (last run date, success rate) to help LLM choose?
- How should we handle cases where multiple projects have very similar names?
- Should we provide different suggestion algorithms for different resource types?

### Future Considerations
- Integration with semantic search for more intelligent matching?
- Learning from LLM correction patterns to improve suggestions over time?
- Expansion to other Azure DevOps resources (repositories, work item types, etc.)?