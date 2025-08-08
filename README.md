# Redfish MCP Server

A Model Context Protocol (MCP) server that enables AI agents and LLMs to control Redfish-enabled hardware and simulators through a secure API. Built with FastMCP for enhanced development experience and structured output.

## Features

This MCP server provides tools for:

- **Power Operations**: Control system power states (On, Off, Restart, etc.)
- **System Inventory**: Get detailed hardware information and specifications
- **Event Logs**: Retrieve and manage system event logs (System, Security, Manager)
- **Health Monitoring**: Monitor system health, status, and sensor readings
- **User Account Management**: Manage BMC user accounts and permissions
- **Sensor Monitoring**: Read temperature, fan, power, and voltage sensors
- **Configuration Management**: Check connection status and auto-configure from environment

## Architecture

- **FastMCP Framework**: Built with FastMCP for better development experience
- **Structured Output**: Uses Pydantic models for type-safe, structured responses
- **Environment Configuration**: Auto-configures from environment variables
- **Secure Authentication**: Username/password authentication with configurable SSL
- **Development Tools**: Compatible with `mcp dev` mode and MCP inspector

## Security

All communications with Redfish endpoints are authenticated using username/password credentials. SSL verification can be configured (disabled by default for self-signed certificates common in BMCs).

## Installation

This project uses `uv` for dependency management:

```bash
# Install dependencies
uv sync

# Install development dependencies
uv sync --group dev
```

## Usage

### Environment Variable Configuration (Recommended)

The simplest way to configure the Redfish MCP server is using environment variables. The server will automatically connect on startup if these are provided:

```bash
export REDFISH_HOST="https://192.168.1.100"
export REDFISH_USERNAME="admin"
export REDFISH_PASSWORD="password123"
export REDFISH_VERIFY_SSL="false"  # Optional, defaults to false
export REDFISH_TIMEOUT="30"        # Optional, defaults to 30 seconds
```

### MCP Client Configuration

Configure the server in your MCP client with environment variables:

#### Claude Desktop
Add to `~/.config/claude-desktop/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "redfish": {
      "command": "uv",
      "args": ["run", "redfish-mcp-server"],
      "cwd": "/path/to/your/redfish-mcp-server",
      "env": {
        "REDFISH_HOST": "https://192.168.1.100",
        "REDFISH_USERNAME": "admin",
        "REDFISH_PASSWORD": "password123",
        "REDFISH_VERIFY_SSL": "false"
      }
    }
  }
}
```

#### Continue.dev
Add to your Continue configuration:

```json
{
  "mcpServers": [
    {
      "name": "redfish",
      "command": "uv",
      "args": ["run", "redfish-mcp-server"],
      "cwd": "/path/to/your/redfish-mcp-server",
      "env": {
        "REDFISH_HOST": "https://192.168.1.100",
        "REDFISH_USERNAME": "admin",
        "REDFISH_PASSWORD": "password123",
        "REDFISH_VERIFY_SSL": "false"
      }
    }
  ]
}
```

### Manual Configuration

If you prefer not to use environment variables, you can use the tools to configure the connection:

1. **Use the `redfish_get_config_status` tool** to check current configuration status
2. **Use the `redfish_configure` tool** to set up connection parameters manually:
   - Host URL (e.g., `https://192.168.1.100`)
   - Username and password for BMC authentication
   - SSL verification settings

3. **Use the available tools** to interact with your Redfish-enabled hardware:

### Available Tools

- `redfish_get_config_status` - Check current configuration status and connection
- `redfish_configure` - Configure connection to Redfish endpoint (if not using env vars)
- `redfish_get_system_info` - Get system information and inventory
- `redfish_power_control` - Control system power state
- `redfish_get_event_logs` - Retrieve system event logs
- `redfish_get_health_status` - Get system health and status
- `redfish_manage_users` - Manage user accounts
- `redfish_get_sensors` - Get sensor readings
- `redfish_clear_logs` - Clear system event logs

### Example Usage

```python
# Check current configuration status
await redfish_get_config_status({})

# If not configured via environment variables, configure manually
await redfish_configure({
    "host": "https://192.168.1.100",
    "username": "admin", 
    "password": "password123",
    "verify_ssl": false
})

# Get system information
await redfish_get_system_info({})

# Power on the system
await redfish_power_control({
    "action": "On"
})

# Check system health
await redfish_get_health_status({})
```

## Development

### FastMCP Development Features

This server is built with FastMCP, providing enhanced development experience:

- **Development Mode**: Use `mcp dev` for hot reloading during development
- **MCP Inspector**: Compatible with MCP inspector for debugging and testing
- **Structured Output**: All responses use Pydantic models for type safety
- **Auto-generated Schemas**: Tools automatically generate JSON schemas from type hints

### Running the Server

```bash
# Set environment variables for automatic configuration
export REDFISH_HOST="https://192.168.1.100"
export REDFISH_USERNAME="admin" 
export REDFISH_PASSWORD="password123"
export REDFISH_VERIFY_SSL="false"

# Run the MCP server in production
uv run redfish-mcp-server

# Run in development mode with hot reloading
uv run mcp dev src/redfish_mcp_server/main.py

# Run with MCP inspector for debugging
uv run mcp inspector src/redfish_mcp_server/main.py
```

### Testing Tools

```bash
# Test the server import
uv run python -c "from redfish_mcp_server.main import mcp; print('Server imported successfully!')"

# Test configuration status
uv run python -c "
from redfish_mcp_server.main import redfish_get_config_status
print(redfish_get_config_status())
"
```

### Code Formatting and Linting

```bash
# Format code
uv run black .

# Lint code  
uv run ruff check .

# Type checking
uv run mypy .
```

### Testing

```bash
# Run tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run specific test
uv run pytest tests/test_main.py::test_redfish_config
```

## Structured Output

This server uses Pydantic models to provide structured, type-safe responses:

### Response Models

- **ConnectionResult**: Connection status and service information
- **SystemInfoResponse**: System inventory and specifications  
- **PowerControlResult**: Power operation results
- **EventLogsResponse**: Event log entries with metadata
- **HealthStatusResponse**: System and chassis health status
- **UserAccountsResponse**: User account information
- **SensorsResponse**: Sensor readings by chassis
- **ConfigStatusResponse**: Configuration and connection status

### Example Response Structure

```json
{
  "systems": [
    {
      "name": "System",
      "model": "PowerEdge R740",
      "manufacturer": "Dell Inc.", 
      "serial_number": "ABC123",
      "power_state": "On",
      "system_type": "Physical",
      "processor_summary": {
        "count": 2,
        "model": "Intel(R) Xeon(R) Gold 6140 CPU @ 2.30GHz"
      },
      "memory_summary": {
        "total_system_memory_gib": 128
      },
      "status": {
        "state": "Enabled",
        "health": "OK"
      }
    }
  ]
}
```

## Supported Redfish Operations

This server implements the most commonly used Redfish operations:

- **System Management**: Power control, system information
- **Monitoring**: Event logs, health status, sensor readings
- **User Management**: Account listing (creation/modification/deletion planned)
- **Inventory**: Hardware components, specifications
- **Configuration**: Connection management and status checking

Additional operations can be added as needed.

## FastMCP Benefits

This implementation uses FastMCP which provides several advantages:

1. **Developer Experience**:
   - Hot reloading with `mcp dev`
   - Built-in debugging with MCP inspector
   - Automatic schema generation from type hints

2. **Type Safety**:
   - Pydantic models for all inputs and outputs
   - Runtime validation of tool parameters
   - Clear error messages for invalid inputs

3. **Structured Output**:
   - Consistent JSON responses with schemas
   - Better integration with AI agents
   - Self-documenting API through type annotations

4. **Simplified Development**:
   - Decorator-based tool registration
   - Automatic parameter parsing
   - Built-in error handling

## Memory Integration

The server can integrate with MCP memory to record operations and maintain context about the hardware being managed. This is optional and will be skipped if memory services are not available.

## Requirements

- Python 3.10+
- Redfish-enabled hardware or simulator
- Network access to BMC/iDRAC/iLO interfaces
- uv package manager

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with appropriate tests
4. Ensure code passes linting and type checking
5. Submit a pull request

## License

[Add your license here]
