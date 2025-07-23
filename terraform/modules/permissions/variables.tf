variable "project_id" {
  description = "The ID of the project for permission setup"
  type        = string
}

variable "github_token" {
  description = "GitHub personal access token for service connection"
  type        = string
  sensitive   = true
}