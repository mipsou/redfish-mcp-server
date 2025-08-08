# Example MCP Client Configuration

This document shows how to configure the Redfish MCP server in various MCP clients. The server uses FastMCP and supports environment variable configuration for easy setup.

## Claude Desktop Configuration

Add to your Claude Desktop configuration file (`~/.config/claude-desktop/claude_desktop_config.json`):

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
        "REDFISH_VERIFY_SSL": "false",
        "REDFISH_TIMEOUT": "30"
      }
    }
  }
}
```

## Continue.dev Configuration

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
        "REDFISH_VERIFY_SSL": "false",
        "REDFISH_TIMEOUT": "30"
      }
    }
  ]
}
```

## Development Mode

For development, you can run with hot reloading:

```bash
cd /path/to/your/redfish-mcp-server
export REDFISH_HOST="https://192.168.1.100"
export REDFISH_USERNAME="admin"
export REDFISH_PASSWORD="password123"
uv run mcp dev src/redfish_mcp_server/main.py
```

## MCP Inspector

For debugging and testing tools:

```bash
cd /path/to/your/redfish-mcp-server
export REDFISH_HOST="https://192.168.1.100" 
export REDFISH_USERNAME="admin"
export REDFISH_PASSWORD="password123"
uv run mcp inspector src/redfish_mcp_server/main.py
```

## Environment Variables

| Variable             | Description                | Required | Default |
| -------------------- | -------------------------- | -------- | ------- |
| `REDFISH_HOST`       | Redfish service URL        | Yes      | -       |
| `REDFISH_USERNAME`   | Authentication username    | Yes      | -       |
| `REDFISH_PASSWORD`   | Authentication password    | Yes      | -       |
| `REDFISH_VERIFY_SSL` | Verify SSL certificates    | No       | `false` |
| `REDFISH_TIMEOUT`    | Request timeout in seconds | No       | `30`    |

## Structured Output

The FastMCP server returns structured data with proper schemas. All tool responses use Pydantic models for type safety and validation.

## Available Tools

- `redfish_get_config_status` - Check configuration and connection status
- `redfish_configure` - Manual configuration (if not using env vars)
- `redfish_get_system_info` - System information and inventory
- `redfish_power_control` - Power management operations
- `redfish_get_event_logs` - Event log retrieval
- `redfish_get_health_status` - Health and status monitoring
- `redfish_manage_users` - User account management
- `redfish_get_sensors` - Sensor readings
- `redfish_clear_logs` - Log management
