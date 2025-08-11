"""System information and inventory tools."""

import logging
from typing import List



from ..config.models import (
    SystemInfo, SystemInfoResponse, ChassisInfo, ManagerInfo
)
from ..utils.exceptions import ConfigurationError, OperationError

logger = logging.getLogger(__name__)

# Global client instance - will be set by main module
redfish_client = None


def set_client(client):
    """Set the global Redfish client instance."""
    global redfish_client
    redfish_client = client


def redfish_get_system_info() -> SystemInfoResponse:
    """
    Get system information and inventory.

    This returns a list of systems with their details including:
    - Basic system information (ID, name, model, manufacturer)
    - Hardware specifications (processors, memory)
    - Power state and system status
    - Associated chassis and managers

    Returns:
        SystemInfoResponse: List of systems with detailed information

    Raises:
        ConfigurationError: If Redfish connection is not configured
        OperationError: If the operation fails
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

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

        logger.info(f"Retrieved information for {len(system_list)} systems")
        return SystemInfoResponse(systems=system_list)

    except Exception as e:
        # Provide user-friendly error messages based on the exception type
        if "authentication failed" in str(e).lower():
            error_msg = "Authentication failed. Please check your username and password."
        elif "access denied" in str(e).lower():
            error_msg = "Access denied. You don't have permission to view system information."
        elif "timeout" in str(e).lower():
            error_msg = "Request timeout. The Redfish service may be slow to respond."
        elif "connection failed" in str(e).lower():
            error_msg = "Connection failed. Please check your network connection and Redfish host URL."
        else:
            error_msg = f"Failed to retrieve system information: {str(e)}"

        logger.error(f"System info error: {error_msg}")
        raise OperationError(error_msg)


def redfish_get_chassis_info() -> List[ChassisInfo]:
    """
    Get chassis information and inventory.

    This returns a list of chassis with their details including:
    - Chassis identification (ID, name)
    - Power state and operational status
    - Health status information

    Returns:
        List[ChassisInfo]: List of chassis with detailed information

    Raises:
        ConfigurationError: If Redfish connection is not configured
        OperationError: If the operation fails
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

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

        logger.info(f"Retrieved information for {len(chassis_list)} chassis")
        return chassis_list

    except Exception as e:
        # Provide user-friendly error messages based on the exception type
        if "authentication failed" in str(e).lower():
            error_msg = "Authentication failed. Please check your username and password."
        elif "access denied" in str(e).lower():
            error_msg = "Access denied. You don't have permission to view chassis information."
        elif "timeout" in str(e).lower():
            error_msg = "Request timeout. The Redfish service may be slow to respond."
        elif "connection failed" in str(e).lower():
            error_msg = "Connection failed. Please check your network connection and Redfish host URL."
        else:
            error_msg = f"Failed to retrieve chassis information: {str(e)}"

        logger.error(f"Chassis info error: {error_msg}")
        raise OperationError(error_msg)


def redfish_get_manager_info() -> List[ManagerInfo]:
    """
    Get manager information and inventory.

    This returns a list of managers with their details including:
    - Manager identification (ID, name, type)
    - Firmware version and operational status
    - Health status and available services
    - Network interfaces and log services

    Returns:
        List[ManagerInfo]: List of managers with detailed information

    Raises:
        ConfigurationError: If Redfish connection is not configured
        OperationError: If the operation fails
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

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
            )
            manager_list.append(manager_info)

        logger.info(f"Retrieved information for {len(manager_list)} managers")
        return manager_list

    except Exception as e:
        # Provide user-friendly error messages based on the exception type
        if "authentication failed" in str(e).lower():
            error_msg = "Authentication failed. Please check your username and password."
        elif "access denied" in str(e).lower():
            error_msg = "Access denied. You don't have permission to view manager information."
        elif "timeout" in str(e).lower():
            error_msg = "Request timeout. The Redfish service may be slow to respond."
        elif "connection failed" in str(e).lower():
            error_msg = "Connection failed. Please check your network connection and Redfish host URL."
        else:
            error_msg = f"Failed to retrieve manager information: {str(e)}"

        logger.error(f"Manager info error: {error_msg}")
        raise OperationError(error_msg)
