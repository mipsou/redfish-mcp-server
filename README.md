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
# Install development dependencies
uv sync
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

#### LM Studio

Add to your LM Studio configuration (`mcp.json`):

```json
{
  "mcpServers": {
      "redfish": {
        "command": "uv",
        "args": [
          "--directory",
          "C:\\Users\\MyUser\\repos\\redfish-mcp-server",
          "run",
          "mcp",
          "run",
          "main.py"
        ],
        "env": {
          "REDFISH_HOST": "http://localhost:8000",
          "REDFISH_USERNAME": "admin",
          "REDFISH_PASSWORD": "password123"
        }
    }
  }
}
```

If developing under Windows with WSL2 where the server is running in WSL, you may need to set the `REDFISH_HOST` to the WSL IP address or use `localhost` if accessing from Windows:

```json
{
  "mcpServers": {
      "redfish": {
        "command": "bash",
        "args": [
          "-c",
          "REDFISH_HOST=http://localhost:8000 REDFISH_USERNAME=admin REDFISH_PASSWORD=password123 /home/carlosedp/.local/bin/uv --directory /home/carlosedp/repos/redfish-mcp-server run mcp run main.py"
        ]
      }
  }
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

### Running the Server for Development

```bash
# Set environment variables for automatic configuration
export REDFISH_HOST="https://192.168.1.100"
export REDFISH_USERNAME="admin"
export REDFISH_PASSWORD="password123"
export REDFISH_VERIFY_SSL="false"

# Run in development mode with the inspector
uv run mcp dev main.py
```

The server requires a Redfish hardware or simulator to connect to. Ensure the Redfish endpoint is accessible and the credentials are correct.

You can use [Redfish-Mockup-Server](https://github.com/DMTF/Redfish-Mockup-Server) for testing with simulated Redfish endpoints. Get the mockup data from the [DMTF Redfish Mockup bundle](https://www.dmtf.org/documents/redfish-spmf/redfish-mockups-bundle-20214).

Unpack them, install dependencies and run the mockup server:

```bash
# Create a venv and install dependencies
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt

# Run the mockup server
python redfishMockupServer.py --short-form -D public-rackmount1`
```
