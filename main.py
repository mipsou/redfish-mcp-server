#!/usr/bin/env python3
"""
Redfish MCP Server

A Model Context Protocol server that provides tools for controlling
Redfish-enabled hardware and simulators.
"""

import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from pydantic import BaseModel, Field
import urllib3

from mcp.server.fastmcp import FastMCP

# Disable SSL warnings for self-signed certificates (common in BMCs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the FastMCP server
mcp = FastMCP("redfish-mcp-server")

class RedfishConfig(BaseModel):
    """Configuration for Redfish connection"""
    host: str = Field(..., description="Redfish host URL")
    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password for authentication")
    verify_ssl: bool = Field(default=False, description="Verify SSL certificates")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class RedfishClient:
    """Client for interacting with Redfish API"""

    def __init__(self, config: RedfishConfig):
        self.config = config
        self.session = requests.Session()
        self.session.auth = (config.username, config.password)
        self.session.verify = config.verify_ssl
        # Set timeout using a wrapper or requests
        self.timeout = config.timeout
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.base_url = config.host.rstrip('/')

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Redfish API"""
        url = urljoin(self.base_url, endpoint)
        try:
            # Add timeout to the request kwargs
            kwargs.setdefault('timeout', self.timeout)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def get(self, endpoint: str) -> Dict[str, Any]:
        """GET request to Redfish API"""
        return self._make_request('GET', endpoint)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST request to Redfish API"""
        return self._make_request('POST', endpoint, json=data)

    def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """PATCH request to Redfish API"""
        return self._make_request('PATCH', endpoint, json=data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request to Redfish API"""
        return self._make_request('DELETE', endpoint)


# Global client instance
redfish_client: Optional[RedfishClient] = None


def _initialize_from_env() -> Optional[RedfishClient]:
    """Initialize Redfish client from environment variables if available"""
    host = os.getenv('REDFISH_HOST')
    username = os.getenv('REDFISH_USERNAME')
    password = os.getenv('REDFISH_PASSWORD')
    verify_ssl = os.getenv('REDFISH_VERIFY_SSL', 'false').lower() in ('true', '1', 'yes')
    timeout = int(os.getenv('REDFISH_TIMEOUT', '30'))

    if host and username and password:
        try:
            config = RedfishConfig(
                host=host,
                username=username,
                password=password,
                verify_ssl=verify_ssl,
                timeout=timeout
            )
            client = RedfishClient(config)

            # Test the connection
            service_root = client.get("/redfish/v1/")
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
        logger.info("  Optional: REDFISH_VERIFY_SSL, REDFISH_TIMEOUT")
        return None


# Try to initialize from environment variables on startup
redfish_client = _initialize_from_env()

# Pydantic models for structured responses
class ConnectionResult(BaseModel):
    """Result of connecting to Redfish service"""
    success: bool
    message: str
    service_name: Optional[str] = None
    version: Optional[str] = None
    uuid: Optional[str] = None


class SystemInfo(BaseModel):
    """System information structure"""
    id: Optional[str] = None
    name: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    power_state: Optional[str] = None
    system_type: Optional[str] = None
    processor_summary: Dict[str, Any] = Field(default_factory=dict)
    memory_summary: Dict[str, Any] = Field(default_factory=dict)
    status: Dict[str, Any] = Field(default_factory=dict)
    chassis: Optional[List[str]] = None  # List of chassis IDs associated with the system
    managers: Optional[List[str]] = None  # List of manager IDs associated with the system

class ChassisInfo(BaseModel):
    """Chassis information structure"""
    id: Optional[str] = None
    name: Optional[str] = None
    power_state: Optional[str] = None
    status: Dict[str, Any] = Field(default_factory=dict)
    health: Optional[str] = None  # e.g., "OK", "Warning", "Critical"

class ManagerInfo(BaseModel):
    """Manager information structure"""
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    firmware_version: Optional[str] = None
    status: Dict[str, Any] = Field(default_factory=dict)
    health: Optional[str] = None  # e.g., "OK", "Warning", "Critical"
    ethernet_interfaces: Optional[Dict[str, Any]] = None
    log_services: Optional[Dict[str, Any]] = None
    servers: Optional[Dict[str, Any]] = None
    chassis: Optional[Dict[str, Any]] = None

class SystemInfoResponse(BaseModel):
    """Response containing list of systems"""
    systems: List[SystemInfo]


class PowerControlResult(BaseModel):
    """Result of power control operation"""
    success: bool
    message: str
    system_id: str
    action: str


class LogEntry(BaseModel):
    """Event log entry"""
    created: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    entry_type: Optional[str] = None


class EventLogsResponse(BaseModel):
    """Response containing event logs"""
    log_type: str
    entries: List[LogEntry]
    count: int


class ChassisHealth(BaseModel):
    """Chassis health information"""
    name: Optional[str] = None
    status: Dict[str, Any] = Field(default_factory=dict)
    power_state: Optional[str] = None


class HealthStatusResponse(BaseModel):
    """System health status response"""
    system_health: Dict[str, Any] = Field(default_factory=dict)
    power_state: Optional[str] = None
    chassis: List[ChassisHealth] = Field(default_factory=list)


class UserAccount(BaseModel):
    """User account information"""
    username: Optional[str] = None
    role_id: Optional[str] = None
    enabled: Optional[bool] = None
    locked: Optional[bool] = None


class UserAccountsResponse(BaseModel):
    """Response containing user accounts"""
    accounts: List[UserAccount]


class SensorDataResponse(BaseModel):
    """Sensor data response"""
    chassis_name: str
    data: Dict[str, Any]


class SensorsResponse(BaseModel):
    """Response containing sensor readings"""
    sensor_type: str
    sensors: List[SensorDataResponse]


class ClearLogsResult(BaseModel):
    """Result of clearing logs"""
    success: bool
    message: str
    log_type: str


class ConfigStatusResponse(BaseModel):
    """Configuration status response"""
    configured: bool
    source: str  # "environment" or "manual"
    host: Optional[str] = None
    username: Optional[str] = None
    verify_ssl: Optional[bool] = None
    timeout: Optional[int] = None
    connection_status: str
    service_info: Optional[Dict[str, Any]] = None


@mcp.tool()
def redfish_get_config_status() -> ConfigStatusResponse:
    """Get current Redfish configuration status"""
    global redfish_client

    if not redfish_client:
        # Check if env vars are available but not configured
        host = os.getenv('REDFISH_HOST')
        username = os.getenv('REDFISH_USERNAME')
        password = os.getenv('REDFISH_PASSWORD')

        if host and username and password:
            return ConfigStatusResponse(
                configured=False,
                source="environment",
                host=host,
                username=username,
                verify_ssl=os.getenv('REDFISH_VERIFY_SSL', 'false').lower() in ('true', '1', 'yes'),
                timeout=int(os.getenv('REDFISH_TIMEOUT', '30')),
                connection_status="not_connected",
                service_info=None
            )
        else:
            return ConfigStatusResponse(
                configured=False,
                source="none",
                connection_status="not_configured"
            )

    # Test current connection
    try:
        service_root = redfish_client.get("/redfish/v1/")
        connection_status = "connected"
        service_info = {
            "name": service_root.get('Name', 'Unknown'),
            "version": service_root.get('RedfishVersion', 'Unknown'),
            "uuid": service_root.get('UUID', 'Unknown')
        }
    except Exception as e:
        connection_status = f"error: {str(e)}"
        service_info = None

    # Determine source (check if current config matches env vars)
    env_host = os.getenv('REDFISH_HOST')
    source = "environment" if env_host == redfish_client.config.host else "manual"

    return ConfigStatusResponse(
        configured=True,
        source=source,
        host=redfish_client.config.host,
        username=redfish_client.config.username,
        verify_ssl=redfish_client.config.verify_ssl,
        timeout=redfish_client.config.timeout,
        connection_status=connection_status,
        service_info=service_info
    )


@mcp.tool()
def redfish_configure(
    host: str,
    username: str,
    password: str,
    verify_ssl: bool = False
) -> ConnectionResult:
    """Configure Redfish connection parameters and test the connection"""
    global redfish_client

    try:
        config = RedfishConfig(
            host=host,
            username=username,
            password=password,
            verify_ssl=verify_ssl
        )
        redfish_client = RedfishClient(config)

        # Test connection
        try:
            service_root = redfish_client.get("/redfish/v1/")
            return ConnectionResult(
                success=True,
                message="Successfully connected to Redfish service",
                service_name=service_root.get('Name', 'Unknown'),
                version=service_root.get('RedfishVersion', 'Unknown'),
                uuid=service_root.get('UUID', 'Unknown')
            )
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"Failed to connect to Redfish service: {str(e)}"
            )
    except Exception as e:
        return ConnectionResult(
            success=False,
            message=f"Configuration error: {str(e)}"
        )


@mcp.tool()
def redfish_get_system_info() -> SystemInfoResponse:
    """
    Get system information and inventory
    This returns a list of systems with their details.
    """
    if not redfish_client:
        raise ValueError("Please configure Redfish connection first using redfish_configure tool.")

    try:
        systems = redfish_client.get("/redfish/v1/Systems/")
        system_list = []

        for system_url in systems.get("Members", []):
            system_data = redfish_client.get(system_url["@odata.id"])
            system_info = SystemInfo(
                id=system_data.get("Id"),
                name=system_data.get("Name"),
                model=system_data.get("Model"),
                manufacturer=system_data.get("Manufacturer"),
                serial_number=system_data.get("SerialNumber"),
                power_state=system_data.get("PowerState"),
                system_type=system_data.get("SystemType"),
                processor_summary=system_data.get("ProcessorSummary", {}),
                memory_summary=system_data.get("MemorySummary", {}),
                status=system_data.get("Status", {}),
                chassis=[chassis["@odata.id"] for chassis in system_data.get("Links", {}).get("Chassis", [])],
                managers=[manager["@odata.id"] for manager in system_data.get("Links", {}).get("ManagedBy", [])]
            )
            system_list.append(system_info)

        return SystemInfoResponse(systems=system_list)
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise


@mcp.tool()
def redfish_get_chassis_info() -> List[ChassisInfo]:
    """
    Get chassis information and inventory
   This returns a list of chassis with their details.
    """
    if not redfish_client:
        raise ValueError("Please configure Redfish connection first using redfish_configure tool.")

    try:
        chassis_data = redfish_client.get("/redfish/v1/Chassis/")
        chassis_list = []

        for chassis_url in chassis_data.get("Members", []):
            chassis_detail = redfish_client.get(chassis_url["@odata.id"])
            chassis_info = ChassisInfo(
                id=chassis_detail.get("Id"),
                name=chassis_detail.get("Name"),
                power_state=chassis_detail.get("PowerState"),
                status=chassis_detail.get("Status", {}),
                health=chassis_detail.get("Status", {}).get("Health", "Unknown")
            )
            chassis_list.append(chassis_info)

        return chassis_list
    except Exception as e:
        logger.error(f"Error getting chassis info: {e}")
        raise


@mcp.tool()
def redfish_get_manager_info() -> List[ManagerInfo]:
    """
    Get manager information and inventory
    This returns a list of managers with their details.
    """
    if not redfish_client:
        raise ValueError("Please configure Redfish connection first using redfish_configure tool.")

    try:
        managers_data = redfish_client.get("/redfish/v1/Managers/")
        manager_list = []

        for manager_url in managers_data.get("Members", []):
            manager_data = redfish_client.get(manager_url["@odata.id"])
            manager_info = ManagerInfo(
                id=manager_data.get("Id"),
                name=manager_data.get("Name"),
                type=manager_data.get("ManagerType"),
                firmware_version=manager_data.get("FirmwareVersion"),
                status=manager_data.get("Status", {}),
                health=manager_data.get("Status", {}).get("Health", "Unknown"),
                ethernet_interfaces=manager_data.get("EthernetInterfaces", {}),
                log_services=manager_data.get("LogServices", {}),
                # servers=manager_data.get("Links", {}),
                # chassis=manager_data.get("Links", {})
            )
            manager_list.append(manager_info)

        return manager_list
    except Exception as e:
        logger.error(f"Error getting manager info: {e}")
        raise

@mcp.tool()
def redfish_power_control(
    action: str,
    system_id: str
) -> PowerControlResult:
    """Control system power state

    Args:
        action: Power action (On, ForceOff, GracefulShutdown, ForceRestart, GracefulRestart)
        system_id: System ID obtained from redfish_get_system_info tool
    """
    if not redfish_client:
        raise ValueError("Please configure Redfish connection first using redfish_configure tool.")

    valid_actions = ["On", "ForceOff", "GracefulShutdown", "ForceRestart", "GracefulRestart"]
    if action not in valid_actions:
        raise ValueError(f"Invalid action. Must be one of: {valid_actions}")

    try:
        power_data = {"ResetType": action}
        redfish_client.post(f"/redfish/v1/Systems/{system_id}/Actions/ComputerSystem.Reset", power_data)

        return PowerControlResult(
            success=True,
            message=f"Power action '{action}' executed successfully",
            system_id=system_id,
            action=action
        )
    except Exception as e:
        logger.error(f"Error executing power control: {e}")
        return PowerControlResult(
            success=False,
            message=f"Failed to execute power action: {str(e)}",
            system_id=system_id,
            action=action
        )


@mcp.tool()
def redfish_get_manager_logs(
    manager_id: str,
    limit: int = 50
) -> EventLogsResponse:
    """
    Retrieve manager event logs

    Args:
        manager_id: ID of the manager to retrieve logs from obtained from redfish_get_manager_info tool
        limit: Maximum number of entries to retrieve
    """
    if not redfish_client:
        raise ValueError("Please configure Redfish connection first using redfish_configure tool.")

    try:
        log_entries = []
        logs_response = redfish_client.get(f"/redfish/v1/Managers/{manager_id}/LogServices/Log/Entries")
        entries = logs_response.get("Members", [])[:limit]

        for entry_url in entries:
            entry_data = redfish_client.get(entry_url["@odata.id"])
            log_entry = LogEntry(
                created=entry_data.get("Created"),
                severity=entry_data.get("Severity"),
                message=entry_data.get("Message"),
                entry_type=entry_data.get("EntryType")
            )
            log_entries.append(log_entry)


        return EventLogsResponse(
            log_type="Manager",
            entries=log_entries,
            count=len(log_entries)
        )
    except Exception as e:
        logger.error(f"Error getting event logs: {e}")
        raise


@mcp.tool()
def redfish_get_health_status(system_id: str) -> HealthStatusResponse:
    """
    Get system health and status information for each system

    Args:
        system_id: System ID obtained from redfish_get_system_info tool
    """
    if not redfish_client:
        raise ValueError("Please configure Redfish connection first using redfish_configure tool.")

    try:
        system_data = redfish_client.get(f"/redfish/v1/Systems/{system_id}")
        chassis_data = redfish_client.get("/redfish/v1/Chassis/")

        chassis_list = []
        for chassis_url in chassis_data.get("Members", []):
            chassis_info = redfish_client.get(chassis_url["@odata.id"])
            chassis_health = ChassisHealth(
                name=chassis_info.get("Name"),
                status=chassis_info.get("Status", {}),
                power_state=chassis_info.get("PowerState")
            )
            chassis_list.append(chassis_health)

        return HealthStatusResponse(
            system_health=system_data.get("Status", {}),
            power_state=system_data.get("PowerState"),
            chassis=chassis_list
        )
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise


@mcp.tool()
def redfish_manage_users(action: str) -> UserAccountsResponse | dict:
    """
    Manage user accounts

    Args:
        action: User management action (currently only 'list' is implemented)
    """
    if not redfish_client:
        raise ValueError("Please configure Redfish connection first using redfish_configure tool.")

    if action == "list":
        try:
            accounts = redfish_client.get("/redfish/v1/AccountService/Accounts/")
            user_list = []

            for account_url in accounts.get("Members", []):
                account_data = redfish_client.get(account_url["@odata.id"])
                user_account = UserAccount(
                    username=account_data.get("UserName"),
                    role_id=account_data.get("RoleId"),
                    enabled=account_data.get("Enabled"),
                    locked=account_data.get("Locked")
                )
                user_list.append(user_account)

            return UserAccountsResponse(accounts=user_list)
        except Exception as e:
            logger.error(f"Error getting user accounts: {e}")
            raise
    else:
        return {"message": f"User management action '{action}' is not yet implemented"}


@mcp.tool()
def redfish_get_sensors(
    system_id: str,
    sensor_type: str = "All"
) -> SensorsResponse:
    """
    Get sensor readings (temperature, fans, power, etc.) for a specific system

    Args:
        system_id: System ID obtained from redfish_get_system_info tool
        sensor_type: Type of sensors to retrieve (Temperature, Fan, All)
    """
    if not redfish_client:
        raise ValueError("Please configure Redfish connection first using redfish_configure tool.")

    valid_sensor_types = ["Temperature", "Fan", "All"]
    if sensor_type not in valid_sensor_types:
        raise ValueError(f"Invalid sensor type. Must be one of: {valid_sensor_types}")

    try:
        # Get the specific system to find its associated chassis
        system_data = redfish_client.get(f"/redfish/v1/Systems/{system_id}")
        system_chassis = system_data.get("Links", {}).get("Chassis", [])

        if not system_chassis:
            # Fallback: if no chassis links found, try to find chassis by other means
            chassis_data = redfish_client.get("/redfish/v1/Chassis/")
            system_chassis = chassis_data.get("Members", [])

        sensor_list = []

        for chassis_ref in system_chassis:
            chassis_url = chassis_ref.get("@odata.id", chassis_ref)
            chassis_info = redfish_client.get(chassis_url)
            chassis_name = chassis_info.get("Name", "Unknown")

            try:
                thermal_data = redfish_client.get(chassis_url + "/Thermal")
                # power_data = redfish_client.get(chassis_url + "/Power")

                # Filter sensor data based on sensor_type
                sensor_data = {}

                if sensor_type in ["Temperature", "All"]:
                    sensor_data["Temperatures"] = thermal_data.get("Temperatures", [])

                if sensor_type in ["Fan", "All"]:
                    sensor_data["Fans"] = thermal_data.get("Fans", [])

                # if sensor_type in ["Power", "All"]:
                #     sensor_data["PowerSupplies"] = power_data.get("PowerSupplies", [])

                # if sensor_type in ["Voltage", "All"]:
                #     sensor_data["Voltages"] = power_data.get("Voltages", [])

            except Exception as e:
                sensor_data = {"error": f"Sensor data not available: {str(e)}"}

            sensor_response = SensorDataResponse(
                chassis_name=chassis_name,
                data=sensor_data
            )
            sensor_list.append(sensor_response)

        return SensorsResponse(
            sensor_type=sensor_type,
            sensors=sensor_list
        )
    except Exception as e:
        logger.error(f"Error getting sensors for system {system_id}: {e}")
        raise


@mcp.tool()
def redfish_clear_logs(log_type: str = "System") -> ClearLogsResult:
    """
    Clear system event logs

    Args:
        log_type: Type of log to clear (System, Security, Manager)
    """
    if not redfish_client:
        raise ValueError("Please configure Redfish connection first using redfish_configure tool.")

    valid_log_types = ["System", "Security", "Manager"]
    if log_type not in valid_log_types:
        raise ValueError(f"Invalid log type. Must be one of: {valid_log_types}")

    try:
        clear_data = {}
        redfish_client.post(f"/redfish/v1/Managers/1/LogServices/{log_type}/Actions/LogService.ClearLog", clear_data)

        return ClearLogsResult(
            success=True,
            message=f"{log_type} logs cleared successfully",
            log_type=log_type
        )
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return ClearLogsResult(
            success=False,
            message=f"Failed to clear {log_type} logs: {str(e)}",
            log_type=log_type
        )
