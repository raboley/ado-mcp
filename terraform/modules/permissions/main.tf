# Note: Service connections and permissions are complex to automate
# This module documents what's needed and provides structure for manual setup

locals {
  required_service_connections = {
    "github-service-connection" = {
      type = "GitHub"
      description = "GitHub service connection for testing repository resources"
      required_for = ["github-resources-test-stable pipeline"]
    }
  }
  
  required_permissions = [
    "Build (read and execute)",
    "Pipeline (read, write, and execute)", 
    "Project (read)",
    "Work Items (read and write)",
    "Test Management (read and write)"
  ]
}

resource "local_file" "permissions_requirements" {
  content = jsonencode({
    service_connections = local.required_service_connections
    permissions = local.required_permissions
    setup_instructions = [
      "1. Service Connections Setup:",
      "   - Go to Project Settings > Service connections",
      "   - Create GitHub service connection",
      "   - Name it 'github-service-connection'", 
      "   - Configure with appropriate GitHub authentication",
      "2. Permissions Setup:",
      "   - Ensure the user/service principal has required permissions",
      "   - Test permissions by running basic operations"
    ]
  })
  filename = "${path.root}/permissions_setup_requirements.json"
}