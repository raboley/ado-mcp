# Project Basics

* Use Taskfile for all build/test command functionality.
* Use uv as the python package manager

# Contribution Requirements

* Always include a new end to end black box test for each feature
* Only use mocks in tests to simulate failure cases for external dependencies we do not control.
* Always add log statements with clear error message and execution context for situations that may go wrong.
* Always Include a doc comment for package functions using the google style.
* Strive to reduce entropy by refactoring and simplifying the codebase where possible once we have working tests for a feature.
