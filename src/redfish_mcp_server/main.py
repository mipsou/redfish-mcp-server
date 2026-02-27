#!/usr/bin/env python3
"""
Redfish MCP Server

A Model Context Protocol server that provides tools for controlling
Redfish-enabled hardware and simulators.
"""

import logging
import os
from typing import Optional

# Conditional import to avoid import errors when MCP is not available
try:
    from mcp.server.fastmcp import FastMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Create a mock FastMCP for testing
    class MockFastMCP:
        def __init__(self, name):
            self.name = name
            self.tools = []

        def tool(self):
            def decorator(func):
                self.tools.append(func)
                return func
            return decorator

        def run(self):
            print(f"Mock MCP server '{self.name}' would run here")

    FastMCP = MockFastMCP

from .client.redfish_client import RedfishClient
from .config.models import RedfishConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the FastMCP server
mcp = FastMCP("redfish-mcp-server")

# Global client instance
redfish_client: Optional[RedfishClient] = None


def _initialize_from_env() -> Optional[RedfishClient]:
    """Initialize Redfish client from environment variables if available"""
    host = os.getenv('REDFISH_HOST')
    username = os.getenv('REDFISH_USERNAME')
    password = os.getenv('REDFISH_PASSWORD')
    verify_ssl = os.getenv('REDFISH_VERIFY_SSL', 'false').lower() in ('true', '1', 'yes')
    timeout = int(os.getenv('REDFISH_TIMEOUT', '30'))
    auth_method = os.getenv('REDFISH_AUTH_METHOD', 'session')
    bmc_vendor = os.getenv('REDFISH_BMC_VENDOR', 'asrockrack')

    if host and username and password:
        try:
            config = RedfishConfig(
                host=host,
                username=username,
                password=password,
                verify_ssl=verify_ssl,
                timeout=timeout,
                auth_method=auth_method,
                bmc_vendor=bmc_vendor,
            )
            client = RedfishClient(config)

            # Test the connection
            service_root = client.test_connection()
            logger.info(f"Auto-configured Redfish client for {host}")
            logger.info(f"Connected to: {service_root.get('Name', 'Unknown')} "
                       f"(Version: {service_root.get('RedfishVersion', 'Unknown')})")
            return client
        except Exception as e:
            logger.warning(f"Failed to auto-configure Redfish client from environment: {e}")
            return None
    else:
        logger.info("Redfish environment variables not set. Use redfish_configure tool or set:")
        logger.info("  REDFISH_HOST, REDFISH_USERNAME, REDFISH_PASSWORD")
        logger.info("  Optional: REDFISH_VERIFY_SSL, REDFISH_TIMEOUT, REDFISH_AUTH_METHOD, REDFISH_BMC_VENDOR")
        return None


def _set_global_client(client: RedfishClient):
    """Set the global client instance and update all tool modules"""
    global redfish_client
    redfish_client = client

    # Import and update all tool modules with the client instance
    from .tools.system import set_client as set_system_client
    from .tools.power import set_client as set_power_client
    from .tools.monitoring import set_client as set_monitoring_client
    from .tools.management import set_client as set_management_client

    set_system_client(client)
    set_power_client(client)
    set_monitoring_client(client)
    set_management_client(client)

    logger.debug("Global client instance set across all tool modules")


def _register_tools():
    """Register all tools with the MCP server"""
    # Import the tool functions from their modules
    from .tools.system import (
        redfish_get_system_info as system_info_func,
        redfish_get_chassis_info as chassis_info_func,
        redfish_get_manager_info as manager_info_func
    )
    from .tools.power import redfish_power_control as power_control_func
    from .tools.monitoring import (
        redfish_get_health_status as health_status_func,
        redfish_get_sensors as sensors_func,
        redfish_get_firmware_inventory as firmware_inventory_func,
        redfish_get_power_consumption as power_consumption_func
    )
    from .tools.management import (
        redfish_manage_users as manage_users_func,
        redfish_get_manager_logs as manager_logs_func,
        redfish_clear_logs as clear_logs_func,
        redfish_get_security_status as security_status_func,
        redfish_get_audit_logs as audit_logs_func,
        redfish_configure as configure_func,
        redfish_get_config_status as config_status_func
    )

    # Register all tools with the main MCP server
    @mcp.tool()
    def redfish_get_system_info():
        """Get system information and inventory"""
        return system_info_func()

    @mcp.tool()
    def redfish_get_chassis_info():
        """Get chassis information and inventory"""
        return chassis_info_func()

    @mcp.tool()
    def redfish_get_manager_info():
        """Get manager information and inventory"""
        return manager_info_func()

    @mcp.tool()
    def redfish_power_control(action: str, system_id: str):
        """Control system power state"""
        return power_control_func(action, system_id)

    @mcp.tool()
    def redfish_get_health_status(system_id: str = None):
        """Get system health and status information for a specific system or all systems"""
        return health_status_func(system_id)

    @mcp.tool()
    def redfish_get_sensors(system_id: str, sensor_type: str = "All"):
        """Get sensor readings for a specific system"""
        return sensors_func(system_id, sensor_type)

    @mcp.tool()
    def redfish_get_firmware_inventory(system_id: str = None):
        """Get firmware inventory information for systems"""
        return firmware_inventory_func(system_id)

    @mcp.tool()
    def redfish_get_power_consumption(system_id: str = None):
        """Get power consumption and efficiency metrics for systems"""
        return power_consumption_func(system_id)

    @mcp.tool()
    def redfish_manage_users(action: str):
        """Manage user accounts on the Redfish system"""
        return manage_users_func(action)

    @mcp.tool()
    def redfish_get_manager_logs(manager_id: str, limit: int = 50):
        """Retrieve manager event logs"""
        return manager_logs_func(manager_id, limit)

    @mcp.tool()
    def redfish_clear_logs(log_type: str = "System"):
        """Clear system event logs"""
        return clear_logs_func(log_type)

    @mcp.tool()
    def redfish_get_security_status():
        """Get security status and compliance information"""
        return security_status_func()

    @mcp.tool()
    def redfish_get_audit_logs(log_type: str = "All", limit: int = 100):
        """Get comprehensive audit logs for security and compliance monitoring"""
        return audit_logs_func(log_type, limit)

    @mcp.tool()
    def redfish_configure(
        host: str,
        username: str,
        password: str,
        verify_ssl: bool = False
    ):
        """Configure Redfish connection parameters and test the connection"""
        result = configure_func(host, username, password, verify_ssl)

        # If successful, update the global client
        if result.success:
            # Get the client from the management module
            from .tools.management import redfish_client as mgmt_client
            if mgmt_client:
                _set_global_client(mgmt_client)

        return result

    @mcp.tool()
    def redfish_get_config_status():
        """Get current Redfish configuration status"""
        return config_status_func()


# Try to initialize from environment variables on startup
initial_client = _initialize_from_env()
if initial_client:
    _set_global_client(initial_client)

# Register all tools
_register_tools()

if __name__ == "__main__":
    # This allows the module to be run directly for testing
    logger.info("Redfish MCP Server initialized")
    logger.info("Available tools:")
    logger.info("  - System information: redfish_get_system_info, redfish_get_chassis_info, redfish_get_manager_info")
    logger.info("  - Power control: redfish_power_control")
    logger.info("  - Monitoring: redfish_get_health_status, redfish_get_sensors")
    logger.info("  - Management: redfish_manage_users, redfish_get_manager_logs, redfish_clear_logs")
    logger.info("  - Configuration: redfish_configure, redfish_get_config_status")
