# Gemini AI Coding Assistant Guidelines

## Introduction

This document provides a set of guidelines for the Gemini AI assistant to follow when working on this project. The purpose of these guidelines is to ensure that all development tasks are completed to a consistent and high standard, resulting in a robust, well-tested, and maintainable codebase.

## Task Completion Checklist

For any given task to be considered "done," the following criteria must be met:

1.  **Working and Executed Code:** The code must be functional and have been successfully executed.
2.  **End-to-End Tests:** Comprehensive end-to-end tests must be written for the new code, without the use of mocks, aiming for 100% code coverage.
3.  **Built-in Observability:** The code and tests must include observability features to handle both "happy path" and "sad path" scenarios.
4.  **AI-Consumable Documentation:** The code must be documented in a way that allows another AI to understand its purpose and usage.
5.  **Successful Test Execution:** All tests must be executed and pass, confirming that they accurately test the intended scenarios.
6.  **Code Commit:** All changes must be committed with a clear and concise commit message.

---

## Project-Specific Tools and Conventions

### Python Package Management

*   **`uv`:** For Python package management, `uv` (https://github.com/astral-sh/uv) should be used. This includes dependency installation, environment management, and package building.

### Task Automation

*   **`Taskfile`:** All major build, test, and development commands should be defined in a `Taskfile` (https://taskfile.dev). This ensures consistency and ease of use across different environments.

## Detailed Guidelines

## Task List Management

Guidelines for managing task lists in markdown files to track progress on completing a PRD

### Task Implementation
- **One sub-task at a time:** Do **NOT** start the next sub‑task until you ask the user for permission and they say "yes" or "y"
- **Completion protocol:**  
  1. When you finish a **sub‑task**, immediately mark it as completed by changing `[ ]` to `[x]`.
  2. If **all** subtasks underneath a parent task are now `[x]`, follow this sequence:
    - **First**: Run the full test suite (`pytest`, `npm test`, `bin/rails test`, etc.)
    - **Only if all tests pass**: Stage changes (`git add .`)
    - **Clean up**: Remove any temporary files and temporary code before committing
    - **Commit**: Use a descriptive commit message that:
      - Uses conventional commit format (`feat:`, `fix:`, `refactor:`, etc.)
      - Summarizes what was accomplished in the parent task
      - Lists key changes and additions
      - References the task number and PRD context
      - **Formats the message as a single-line command using `-m` flags**
  3. Once all the subtasks are marked completed and changes have been committed, mark the **parent task** as completed.
- Stop after each sub‑task and wait for the user's go‑ahead.

### Task List Maintenance

1. **Update the task list as you work:**
   - Mark tasks and subtasks as completed (`[x]`) per the protocol above.
   - Add new tasks as they emerge.

2. **Maintain the "Relevant Files" section:**
   - List every file created or modified.
   - Give each file a one‑line description of its purpose.

### AI Instructions

When working with task lists, the AI must:

1. Regularly update the task list file after finishing any significant work.
2. Follow the completion protocol:
   - Mark each finished **sub‑task** `[x]`.
   - Mark the **parent task** `[x]` once **all** its subtasks are `[x]`.
3. Add newly discovered tasks.
4. Keep "Relevant Files" accurate and up to date.
5. Before starting work, check which sub‑task is next.
6. After implementing a sub‑task, update the file and then pause for user approval.

## Detailed Guidelines

### 1. Writing Working Code

Before submitting any code, ensure that it is not only well-written but also fully functional. You should attempt to run the code to validate its correctness.

### 2. End-to-End Testing

-   **No Mocks:** All tests should be end-to-end and test the full functionality of the code. Avoid using mocks or stubs.
-   **Comprehensive Scenarios:** Tests should cover all aspects of the new feature, including edge cases and potential failure points.

### 3. Observability

-   **Logging:** Implement structured logging to provide clear insights into the application's behavior.
-   **Happy and Sad Paths:** Ensure that your tests and observability measures cover both successful execution (the "happy path") and potential errors or failures (the "sad path"). This will help in debugging and understanding the application's behavior in various scenarios.

### 4. AI-Consumable Documentation

-   **Docstrings:** All functions, classes, and modules should have clear and concise docstrings that explain their purpose, arguments, and return values.
-   **Focus on "Why" and "When":** The documentation should not just describe *what* the code does, but *why* it is needed and *when* it should be used. This will help other AI assistants understand the context and make better decisions.

### 5. Test Execution and Validation

-   **Run All Tests:** Before committing any changes, execute all relevant tests and ensure that they pass.
-   **Verify Test Scenarios:** Double-check that the tests are actually testing the intended scenarios and are not just passing due to a flaw in the test itself.

### 6. Committing Changes

-   **Concise and Helpful Messages:** Write a commit message that is both concise and informative. The title should summarize the change, and the body (if needed) should provide additional context.
-   **Atomic Commits:** Each commit should represent a single logical change. Avoid bundling unrelated changes into a single commit.
