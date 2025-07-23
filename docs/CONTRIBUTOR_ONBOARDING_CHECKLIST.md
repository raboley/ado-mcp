# Contributor Onboarding Checklist

## Welcome to ADO-MCP! 🎉

This checklist will guide you through setting up your development environment and making your first contribution to the ado-mcp project.

## Prerequisites ✅

Before starting, ensure you have these tools installed:

- [ ] **Python 3.11+**: Check with `python --version`
- [ ] **UV Package Manager**: Install from [astral.sh/uv](https://astral.sh/uv)
- [ ] **Git**: For version control
- [ ] **Azure DevOps Account**: With organization access for testing
- [ ] **GitHub Account**: For contributing to the project

## Initial Setup (30 minutes)

### 1. Repository Setup
- [ ] Fork the repository on GitHub
- [ ] Clone your fork locally:
  ```bash
  git clone https://github.com/YOUR_USERNAME/ado-mcp.git
  cd ado-mcp
  ```
- [ ] Add upstream remote:
  ```bash
  git remote add upstream https://github.com/ORIGINAL_OWNER/ado-mcp.git
  ```

### 2. Development Environment
- [ ] Install dependencies:
  ```bash
  task install
  ```
- [ ] Verify installation:
  ```bash
  uv --version
  task --version
  ```

### 3. Azure DevOps Credentials
- [ ] Create Azure DevOps Personal Access Token:
  1. Go to `https://dev.azure.com/[YourOrg]/_usersSettings/tokens`
  2. Click "New Token"
  3. Set permissions:
     - **Project and team**: read, write, & manage
     - **Build**: read & execute
     - **Code**: read
     - **Work items**: read & write
  4. Copy the token (you won't see it again!)

- [ ] Set up environment file:
  ```bash
  task setup-env
  # Edit .env file with your actual values
  ```

### 4. Test Environment Setup (15 minutes)
- [ ] Provision test infrastructure:
  ```bash
  task ado-up
  ```
- [ ] Verify setup with tests:
  ```bash
  task test
  ```
- [ ] All tests should pass (472/472) ✅

## Understanding the Codebase (60 minutes)

### 5. Project Structure
- [ ] Read `PLANNING.md` - High-level architecture and design decisions
- [ ] Read `README.md` - Project overview and usage
- [ ] Review `CLAUDE.md` - Development workflow and conventions
- [ ] Explore the main directories:
  - [ ] `ado/` - Core Azure DevOps integration logic
  - [ ] `server.py` - MCP server implementation  
  - [ ] `tests/` - Comprehensive test suite
  - [ ] `docs/` - Documentation and guides

### 6. Key Concepts
- [ ] **MCP (Model Context Protocol)**: Understand how Claude integrates with external tools
- [ ] **Azure DevOps APIs**: Review `ado/client.py` for API integration patterns
- [ ] **Terraform Infrastructure**: Examine `terraform/` for test environment automation
- [ ] **Test Configuration**: Study `src/test_config.py` for dynamic configuration

### 7. Code Quality Standards
- [ ] Review existing tests to understand testing patterns
- [ ] Check `pyproject.toml` for code style configuration
- [ ] Run linting: `task format` and `task lint`
- [ ] Understand the commit workflow from `CLAUDE.md`

## Making Your First Contribution (90 minutes)

### 8. Find an Issue
- [ ] Browse [GitHub Issues](https://github.com/project/ado-mcp/issues)
- [ ] Look for issues labeled `good first issue` or `help wanted`
- [ ] Comment on the issue to express interest
- [ ] Discuss approach with maintainers if needed

### 9. Development Workflow
- [ ] Create a feature branch:
  ```bash
  git checkout -b feature/your-feature-name
  ```
- [ ] Make your changes following the coding standards
- [ ] Write or update tests for your changes
- [ ] Run the test suite: `task test`
- [ ] Ensure all tests pass

### 10. Code Quality Checks
- [ ] Format code: `task format`
- [ ] Run linting: `task lint`  
- [ ] Check type hints: `task typecheck` (if available)
- [ ] Verify no security issues in dependencies
- [ ] Add docstrings for new public functions

### 11. Testing Your Changes
- [ ] Run specific tests related to your changes:
  ```bash
  task test-single TEST_NAME=tests/path/to/your/test.py
  ```
- [ ] Test manually if applicable:
  ```bash
  task dev  # Start development server
  ```
- [ ] Create end-to-end tests for user-facing features
- [ ] Verify your changes don't break existing functionality

### 12. Documentation
- [ ] Update relevant documentation if your changes affect:
  - [ ] API functionality
  - [ ] Installation process
  - [ ] Configuration options
  - [ ] User workflows
- [ ] Add code comments for complex logic
- [ ] Update changelog if applicable

## Submitting Your Contribution

### 13. Pre-submission Checklist
- [ ] All tests pass: `task test`
- [ ] Code is properly formatted: `task format`
- [ ] No linting errors: `task lint`
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] Branch is up-to-date with main:
  ```bash
  git fetch upstream
  git rebase upstream/main
  ```

### 14. Pull Request
- [ ] Push your branch to your fork:
  ```bash
  git push origin feature/your-feature-name
  ```
- [ ] Create a Pull Request on GitHub
- [ ] Fill out the PR template completely
- [ ] Link to related issues
- [ ] Request review from maintainers
- [ ] Respond to feedback promptly

### 15. After Submission
- [ ] Monitor CI/CD checks
- [ ] Address any failing checks
- [ ] Respond to code review comments
- [ ] Make requested changes in additional commits
- [ ] Keep the PR updated with main branch if needed

## Ongoing Contribution

### 16. Staying Connected
- [ ] Star the repository to get updates
- [ ] Watch for new issues and discussions
- [ ] Join community discussions in issues/PRs
- [ ] Help review other contributors' PRs
- [ ] Share feedback on project direction

### 17. Advanced Topics (Optional)
- [ ] Understand MCP protocol specification
- [ ] Learn about Azure DevOps API advanced features
- [ ] Explore Terraform provider capabilities
- [ ] Study CI/CD pipeline configuration
- [ ] Review security best practices

## Common Pitfalls & Solutions

### Environment Issues
- **Tests failing locally**: 
  - Ensure `task ado-up` completed successfully
  - Check that all required environment variables are set
  - Verify your PAT has correct permissions

- **Import errors**:
  - Run `task install` to ensure all dependencies are installed
  - Check that you're using the correct Python version

### Development Issues  
- **Terraform errors**:
  - Check your Azure DevOps organization URL is correct
  - Ensure your PAT token hasn't expired
  - Try `task ado-down` then `task ado-up` to recreate environment

- **Test timeouts**:
  - The test suite uses a 300-second timeout for long operations
  - Some tests require network connectivity to Azure DevOps
  - Use `task test-sequential` for debugging individual test failures  

### Code Quality Issues
- **Linting failures**:
  - Run `task format` to auto-fix formatting issues
  - Check `pyproject.toml` for project-specific style rules
  - Install recommended VS Code extensions for automatic formatting

- **Type checking errors**:
  - Add proper type hints to new functions
  - Import types from `typing` module when needed
  - Use Pydantic models for data structures

## Getting Help

### Resources
- [ ] **Documentation**: Start with `docs/` directory
- [ ] **Code Examples**: Review existing similar implementations
- [ ] **Tests**: Check test files for usage patterns
- [ ] **Issues**: Search existing issues for similar problems

### Asking for Help
- [ ] Search existing issues and discussions first
- [ ] Provide complete error messages and stack traces
- [ ] Include your environment details (OS, Python version, etc.)
- [ ] Share minimal reproducible examples
- [ ] Be specific about what you expected vs. what happened

### Community
- [ ] **GitHub Discussions**: For design questions and ideas
- [ ] **Issues**: For bug reports and feature requests  
- [ ] **Pull Requests**: For code review and implementation discussion
- [ ] **Security Issues**: Use GitHub Security Advisories for vulnerabilities

## Success Criteria

You've successfully onboarded when you can:

- [ ] ✅ Set up development environment from scratch
- [ ] ✅ Run the full test suite successfully (472/472 tests pass)
- [ ] ✅ Make a meaningful code change
- [ ] ✅ Write appropriate tests for your change
- [ ] ✅ Submit a well-formatted pull request
- [ ] ✅ Respond to code review feedback
- [ ] ✅ See your contribution merged! 🎉

## Recognition

Once you've made your first contribution:
- [ ] Add yourself to `CONTRIBUTORS.md` (if it exists)
- [ ] Update your GitHub profile to show your contribution
- [ ] Share your success with the community!
- [ ] Consider becoming a regular contributor

---

## Welcome to the Team! 🚀

Thank you for contributing to ado-mcp! Your efforts help make Azure DevOps integration better for AI assistants and developers everywhere.

**Questions?** Don't hesitate to ask in issues or discussions. The maintainers and community are here to help you succeed.

**Next Steps**: After your first contribution, consider tackling more complex features, helping with documentation, or mentoring other new contributors.

Happy coding! 🎯