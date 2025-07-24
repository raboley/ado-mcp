variable "project_name" {
  description = "Name of the test project to create"
  type        = string
  default     = "ado-mcp-test"
}

variable "project_description" {
  description = "Description for the test project"
  type        = string
  default     = "Test project for ado-mcp integration testing"
}

variable "github_token" {
  description = "GitHub personal access token for service connections"
  type        = string
  sensitive   = true
}