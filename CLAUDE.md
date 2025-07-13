### 🔄 Project Awareness & Context
- **Always read `PLANNING.md`** at the start of a new conversation to understand the project's architecture, goals, style, and constraints.
- **Check `TASK.md`** before starting a new task. If the task isn’t listed, add it with a brief description and today's date.
- **Check CONTRIBUTING.md** when working on tasks.
- **Use consistent naming conventions, file structure, and architecture patterns** as described in `PLANNING.md`.
- **Use venv_linux** (the virtual environment) whenever executing Python commands, including for tests.
- **Read [NEW_TOOL_WORKFLOW.md](NEW_TOOL_WORKFLOW.md)** when asked to create a new tool

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
  For agents this looks like:
    - `agent.py` - Main agent definition and execution logic 
    - `tools.py` - Tool functions used by the agent 
    - `prompts.py` - System prompts
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.
- **Use logging module to add observability** Any errors must include all relevant execution context so an llm can fix it.

### 🧪 Testing & Reliability
- **Always create Pytest end to end tests for new features** that a user can experience.
- **Only create end to end tests using actual data and real connections** - black box test how a user would test.
- **ALWAYS use `task test` to run tests** - never run pytest directly. This ensures proper environment variables are sourced.
- **Tests run in parallel by default** using pytest-xdist for faster execution (~15s vs 80s):
  - Use `task test` for parallel execution (default)
  - Use `task test-sequential` for debugging when you need sequential execution
  - Use `task test-single TEST_NAME=path::to::test` for individual test execution
- **Tests require ADO credentials** - AZURE_DEVOPS_EXT_PAT and ADO_ORGANIZATION_URL must be set via Taskfile.
- **FastMCP converts Pydantic models to dictionaries** - tests should expect dictionary responses, not Pydantic objects.
- **Dedicated test pipelines** are pre-created for pipeline run tests to avoid create/delete overhead.
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it. use `task test` to ensure everything still works
- **Tests should live in a `/tests` folder** mirroring the main app structure.
- **NEVER use mocking in tests.** 
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case
    - 1 test to ensure tools and resources are added to the mcp server.

### ✅ Task Completion
- **Always Run tests** ensuring they all pass using `task test` before marking something complete
- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `TASK.md` under a “Discovered During Work” section.
- Request Feedback from the human before moving on to the next feature task.

### 📎 Style & Conventions
- **Use Python** as the primary language.
- **Use uv** as the package manager [uv](https://github.com/astral-sh/uv)
- **Use Taskfile** for all build and test commands.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- **Strongly type data structures** create datatypes for structures we receive or send.
- Use `FastAPI` for APIs and `SQLAlchemy` or `SQLModel` for ORM if applicable.
- Write **docstrings for every public function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to or if part of a task from `TASK.md`.

### 📝 AI Planning
- **Always Plan Features Vertically** A new feature should include:
  - Code
  - End to End tests
  - Observability
  - Code Doc comments