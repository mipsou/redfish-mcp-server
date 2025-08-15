# Copilot Instructions for AI Agents

## Project Overview

- **Redfish MCP Server**: Modular Python server for controlling Redfish-enabled hardware via Model Context Protocol (MCP).
- **Main entry**: `src/redfish_mcp_server/main.py` orchestrates tool registration and MCP integration.
- **Modular structure**: Core logic split into `config/`, `client/`, `tools/`, and `utils/` submodules for maintainability and testability.

## Key Architectural Patterns

- **Business logic**: Each tool (system, power, monitoring, management) is implemented in its own file under `src/redfish_mcp_server/tools/`.
- **Tool registration**: Only the main module applies MCP decorators (`@mcp.tool()`), keeping tool modules pure and testable.
- **Data models**: All Pydantic models are centralized in `src/redfish_mcp_server/config/models.py` for type-safe, structured responses.
- **Custom exceptions**: Error handling uses a hierarchy in `src/redfish_mcp_server/utils/exceptions.py` (e.g., `RedfishError`, `ConnectionError`).
- **Environment config**: Connection parameters are auto-loaded from environment variables if present; manual configuration via tool functions is also supported.

## Developer Workflows

- **Install dependencies**: `uv sync` (add `--group dev` for dev dependencies)
- **Run server**: `uv run redfish-mcp-server` (prod), `uv run mcp dev src/redfish_mcp_server/main.py` (dev/hot reload)
- **Debug/inspect**: `uv run mcp inspector src/redfish_mcp_server/main.py`
- **Test**: `uv run pytest` (all), `uv run pytest -v` (verbose), `uv run pytest tests/test_main.py::test_redfish_config` (specific)
- **Lint/format/typecheck**: `uv run black .`, `uv run ruff check .`, `uv run mypy .`

## Project-Specific Conventions

- **Case-insensitive actions**: Power control and similar tools accept action names in any case.
- **Structured output**: All tool responses use Pydantic models; see `models.py` for schema details.
- **Conditional MCP imports**: Tool modules avoid direct MCP dependencies for easier testing and development.
- **Centralized tool registration**: Only register tools in the main module to ensure MCP inspector visibility and avoid duplicates.

## Integration Points

- **Redfish API**: All hardware communication via Redfish API, implemented in `client/redfish_client.py`.
- **MCP memory**: Optional integration for operation context; gracefully skipped if unavailable.
- **Environment variables**: Used for configuration; see README for required variables.

## Examples

- To add a new tool: create a function in the appropriate `tools/` module, then register it in `main.py` with `@mcp.tool()`.
- To extend data models: update or add Pydantic models in `config/models.py`.
- To handle new error types: subclass from `RedfishError` in `utils/exceptions.py`.

## References

- See `MODULAR_STRUCTURE.md` for architectural rationale and migration notes.
- See `README.md` for setup, usage, and workflow details.
- Key files: `src/redfish_mcp_server/main.py`, `src/redfish_mcp_server/tools/`, `src/redfish_mcp_server/config/models.py`, `src/redfish_mcp_server/utils/exceptions.py`.

---

If any section is unclear or missing important project-specific details, please provide feedback to improve these instructions.
