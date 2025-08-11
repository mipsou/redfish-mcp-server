"""MCP tools for Redfish operations."""

from .system import *
from .power import *
from .monitoring import *
from .management import *

__all__ = [
    # System tools
    "redfish_get_system_info",
    "redfish_get_chassis_info",
    "redfish_get_manager_info",
    # Power tools
    "redfish_power_control",
    # Monitoring tools
    "redfish_get_health_status",
    "redfish_get_sensors",
    # Management tools
    "redfish_manage_users",
    "redfish_get_manager_logs",
    "redfish_clear_logs",
    # Configuration tools
    "redfish_configure",
    "redfish_get_config_status",
]
