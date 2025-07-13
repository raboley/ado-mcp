"""
Helper tools for intelligent parsing and user-friendly ADO operations.

This module provides high-level tools that automatically handle various user input formats
like URLs, pipeline names, YAML files, etc. and convert them to the appropriate ADO operations.
"""

import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


class AdoInputParser:
    """Intelligent parser for various Azure DevOps input formats."""

    @staticmethod
    def parse_ado_url(url: str) -> dict[str, str | int | None]:
        """
        Parse an Azure DevOps URL to extract organization, project, and build/pipeline information.

        Supports formats like:
        - https://dev.azure.com/Org/Project/_build/results?buildId=123
        - https://dev.azure.com/Org/Project/_build/definition?definitionId=456
        - https://dev.azure.com/Org/Project/_apps/hub/ms.vss-ciworkflow.build-ci-hub

        Returns:
            Dict with keys: organization, project, build_id, pipeline_id, url_type
        """
        try:
            parsed = urlparse(url)

            # Extract organization and project from path
            path_parts = [p for p in parsed.path.split("/") if p]

            if len(path_parts) < 2:
                return {"error": "Invalid Azure DevOps URL format"}

            organization = path_parts[0]
            project = path_parts[1]

            # Parse query parameters
            query_params = parse_qs(parsed.query)

            result: dict[str, str | int | None] = {
                "organization": organization,
                "project": project,
                "build_id": None,
                "pipeline_id": None,
                "url_type": "unknown",
            }

            # Determine URL type and extract IDs
            if "_build/results" in parsed.path:
                result["url_type"] = "build_results"
                if "buildId" in query_params:
                    result["build_id"] = int(query_params["buildId"][0])
            elif "_build/definition" in parsed.path:
                result["url_type"] = "pipeline_definition"
                if "definitionId" in query_params:
                    result["pipeline_id"] = int(query_params["definitionId"][0])
            elif "_build" in parsed.path:
                result["url_type"] = "build_hub"

            return result

        except Exception as e:
            logger.error(f"Failed to parse ADO URL: {e}")
            return {"error": f"Failed to parse URL: {str(e)}"}

    @staticmethod
    def extract_pipeline_info_from_text(text: str) -> dict[str, list[str]]:
        """
        Extract pipeline-related information from free-form text.

        Looks for:
        - Pipeline names (quoted or unquoted)
        - YAML file paths (*.yml, *.yaml)
        - Build numbers
        - URLs

        Returns:
            Dict with potential pipeline names, yaml files, build numbers, urls
        """
        result: dict[str, list[str]] = {
            "pipeline_names": [],
            "yaml_files": [],
            "build_numbers": [],
            "urls": [],
        }

        # Find URLs
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, text)
        result["urls"] = urls

        # Find YAML files
        yaml_pattern = r"[\w\-\/\.]+\.ya?ml"
        yaml_files = re.findall(yaml_pattern, text, re.IGNORECASE)
        result["yaml_files"] = yaml_files

        # Find quoted pipeline names
        quoted_pattern = r'["\']([^"\']+)["\']'
        quoted_names = re.findall(quoted_pattern, text)
        result["pipeline_names"].extend(quoted_names)

        # Find build numbers (numeric sequences that might be build IDs)
        build_pattern = r"\b\d{2,6}\b"  # 2-6 digit numbers
        build_numbers = re.findall(build_pattern, text)
        result["build_numbers"] = build_numbers

        return result


def register_helper_tools(mcp_instance, client_container):
    """Register intelligent helper tools with the MCP instance."""

    @mcp_instance.tool
    def analyze_pipeline_input(
        user_input: str, organization: str | None = None, project: str | None = None
    ) -> dict:
        """
        Intelligently analyze user input to determine what pipeline operation they want.

        This is the main entry point for LLMs when users provide:
        - Azure DevOps URLs (build results, pipeline definitions, etc.)
        - Pipeline names (quoted or unquoted)
        - YAML file references
        - Build numbers or IDs
        - Mixed text with pipeline information

        The tool will parse the input and provide guidance on which specific tools to use next.

        Args:
            user_input (str): The raw user input (URL, pipeline name, description, etc.)
            organization (str, optional): Organization name if known
            project (str, optional): Project name if known

        Returns:
            Dict: Analysis results with suggested next steps and extracted information
        """
        logger.info(f"Analyzing pipeline input: {user_input[:100]}...")

        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            return {
                "error": "ADO client not available",
                "suggestion": "Use set_ado_organization tool first",
            }

        result: dict[str, Any] = {
            "input_type": "unknown",
            "extracted_info": {},
            "next_steps": [],
            "confidence": "low",
        }

        # Check if input is a URL
        if user_input.strip().startswith("http"):
            url_info = AdoInputParser.parse_ado_url(user_input.strip())
            if "error" not in url_info:
                result["input_type"] = "azure_devops_url"
                result["extracted_info"] = url_info
                result["confidence"] = "high"

                if url_info["build_id"]:
                    result["next_steps"] = [
                        f"Use get_build_by_id with project_id and build_id={url_info['build_id']} to get pipeline details",
                        "Then use get_pipeline_run or get_pipeline_failure_summary for analysis",
                    ]
                elif url_info["pipeline_id"]:
                    result["next_steps"] = [
                        f"Use get_pipeline with project_id and pipeline_id={url_info['pipeline_id']} for pipeline details",
                        "Use run_pipeline to execute the pipeline",
                    ]

                # Override org/project if found in URL
                organization = str(url_info["organization"]) if url_info["organization"] else None
                project = str(url_info["project"]) if url_info["project"] else None
            else:
                result["error"] = str(url_info["error"]) if url_info["error"] else None
        else:
            # Parse text for pipeline information
            text_info = AdoInputParser.extract_pipeline_info_from_text(user_input)
            result["extracted_info"] = text_info

            if text_info["urls"]:
                result["input_type"] = "text_with_urls"
                result["next_steps"] = ["Analyze each URL found in the text"]
            elif text_info["yaml_files"]:
                result["input_type"] = "yaml_reference"
                result["next_steps"] = [
                    "Use list_pipelines to find pipelines",
                    "Search for pipelines that reference the YAML files mentioned",
                ]
            elif text_info["pipeline_names"]:
                result["input_type"] = "pipeline_name"
                result["next_steps"] = [
                    "Use list_pipelines to find matching pipeline names",
                    "Use fuzzy matching on pipeline names",
                ]
            elif text_info["build_numbers"]:
                result["input_type"] = "build_numbers"
                result["next_steps"] = [
                    f"Try get_build_by_id with build_id={text_info['build_numbers'][0]} for the most likely build number"
                ]

        # Add organization/project info
        if organization and project:
            result["suggested_params"] = {"organization": organization, "project": project}
            result["next_steps"].append("Organization and project are known - ready to proceed")
        else:
            result["next_steps"].append("Use list_projects to find the correct project_id first")

        return result

    @mcp_instance.tool
    def find_pipeline_by_name(
        pipeline_name: str, project_id: str, exact_match: bool = False
    ) -> dict:
        """
        Find a pipeline by name with fuzzy matching support.

        This tool helps when users provide pipeline names instead of IDs.
        It will search through all pipelines and find the best matches.

        Args:
            pipeline_name (str): The pipeline name to search for
            project_id (str): The project ID to search within
            exact_match (bool): Whether to require exact match or allow fuzzy matching

        Returns:
            Dict: Found pipelines with match scores and suggested actions
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            return {"error": "ADO client not available"}

        try:
            # Get all pipelines
            pipelines = ado_client_instance.list_pipelines(project_id)

            matches: list[dict[str, Any]] = []
            pipeline_name_lower = pipeline_name.lower()

            for pipeline in pipelines:
                # Handle both Pydantic objects and dictionaries
                if hasattr(pipeline, "name"):
                    pipeline_name_actual = pipeline.name.lower()
                    pipeline_dict = {
                        "id": pipeline.id,
                        "name": pipeline.name,
                        "url": getattr(pipeline, "url", ""),
                        "folder": getattr(pipeline, "folder", ""),
                    }
                else:
                    pipeline_name_actual = pipeline.get("name", "").lower()
                    pipeline_dict = pipeline

                if exact_match:
                    if pipeline_name_lower == pipeline_name_actual:
                        matches.append(
                            {"pipeline": pipeline_dict, "match_type": "exact", "confidence": 1.0}
                        )
                else:
                    # Fuzzy matching
                    if pipeline_name_lower == pipeline_name_actual:
                        match_type = "exact"
                        confidence = 1.0
                    elif pipeline_name_lower in pipeline_name_actual:
                        match_type = "contains"
                        confidence = 0.8
                    elif pipeline_name_actual in pipeline_name_lower:
                        match_type = "contained_in"
                        confidence = 0.7
                    elif any(word in pipeline_name_actual for word in pipeline_name_lower.split()):
                        match_type = "word_match"
                        confidence = 0.6
                    else:
                        continue

                    matches.append(
                        {
                            "pipeline": pipeline_dict,
                            "match_type": match_type,
                            "confidence": confidence,
                        }
                    )

            # Sort by confidence
            matches.sort(key=lambda x: float(x["confidence"]), reverse=True)

            result = {
                "search_term": pipeline_name,
                "total_matches": len(matches),
                "matches": matches[:5],  # Top 5 matches
                "suggested_actions": [],
            }

            if matches:
                best_match: dict[str, Any] = matches[0]
                if float(best_match["confidence"]) >= 0.8:
                    pipeline_info = best_match["pipeline"]
                    result["suggested_actions"] = [
                        f"Use pipeline_id={pipeline_info['id']} for '{pipeline_info['name']}'",
                        "High confidence match found",
                    ]
                else:
                    result["suggested_actions"] = [
                        "Multiple potential matches found",
                        "Review the matches and select the correct pipeline_id",
                    ]
            else:
                result["suggested_actions"] = [
                    "No matches found",
                    "Try list_pipelines to see all available pipelines",
                    "Check if the pipeline name is correct",
                ]

            return result

        except Exception as e:
            logger.error(f"Error finding pipeline by name: {e}")
            return {"error": f"Failed to search pipelines: {str(e)}"}

    @mcp_instance.tool
    def resolve_pipeline_from_url(url: str) -> dict:
        """
        Complete pipeline resolution from Azure DevOps URL.

        This tool takes an Azure DevOps URL and resolves it to specific pipeline
        and run information, ready for use with other tools.

        Args:
            url (str): Azure DevOps URL (build results, pipeline definition, etc.)

        Returns:
            Dict: Resolved pipeline information with project_id, pipeline_id, run_id, etc.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            return {"error": "ADO client not available"}

        # Parse the URL
        url_info = AdoInputParser.parse_ado_url(url)
        if "error" in url_info:
            return url_info

        try:
            # Find the project
            projects = ado_client_instance.list_projects()
            project = None
            for p in projects:
                # Handle both Pydantic objects and dictionaries
                if hasattr(p, "name"):
                    project_name = p.name
                    project_id = p.id
                else:
                    project_name = p["name"]
                    project_id = p["id"]

                if (
                    project_name
                    and url_info["project"]
                    and project_name.lower() == str(url_info["project"]).lower()
                ):
                    project = {"id": project_id, "name": project_name}
                    break

            if not project:
                available_names = []
                for p in projects:
                    if hasattr(p, "name"):
                        available_names.append(p.name)
                    else:
                        available_names.append(p["name"])

                return {
                    "error": f"Project '{url_info['project']}' not found",
                    "available_projects": available_names,
                }

            result = {
                "url_info": url_info,
                "project_id": project["id"],
                "project_name": project["name"],
                "organization": url_info["organization"],
            }

            # If it's a build URL, resolve the pipeline
            if url_info["build_id"]:
                build_details = ado_client_instance.get_build_by_id(
                    project["id"], url_info["build_id"]
                )
                result.update(
                    {
                        "build_id": url_info["build_id"],
                        "pipeline_id": build_details["definition"]["id"],
                        "pipeline_name": build_details["definition"]["name"],
                        "build_status": build_details.get("status"),
                        "build_result": build_details.get("result"),
                        "suggested_actions": [
                            f"Use get_pipeline_run with pipeline_id={build_details['definition']['id']} and run_id={url_info['build_id']}",
                            "Use get_pipeline_failure_summary if the build failed",
                            "Use get_failed_step_logs for detailed error analysis",
                        ],
                    }
                )
            elif url_info["pipeline_id"]:
                pipeline_details = ado_client_instance.get_pipeline(
                    project["id"], url_info["pipeline_id"]
                )
                result.update(
                    {
                        "pipeline_id": url_info["pipeline_id"],
                        "pipeline_name": pipeline_details.get("name"),
                        "suggested_actions": [
                            f"Use run_pipeline with pipeline_id={url_info['pipeline_id']} to execute",
                            "Use get_pipeline for detailed pipeline configuration",
                            "Use preview_pipeline to see what the pipeline would do",
                        ],
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error resolving pipeline from URL: {e}")
            return {"error": f"Failed to resolve pipeline: {str(e)}"}
