"""Monitoring tools for system health and sensors."""

import logging
from typing import List



from ..config.models import (
    HealthStatusResponse, ChassisHealth, SensorsResponse, SensorDataResponse
)
from ..utils.exceptions import ConfigurationError, ValidationError, OperationError

logger = logging.getLogger(__name__)

# Global client instance - will be set by main module
redfish_client = None


def set_client(client):
    """Set the global Redfish client instance."""
    global redfish_client
    redfish_client = client


def redfish_get_health_status(system_id: str = None) -> HealthStatusResponse:
    """
    Get system health and status information.

    This tool provides comprehensive health information including:
    - Overall system health status
    - Current power state
    - Chassis health information
    - Status details for all components

    If system_id is not provided, the tool will return the health status for all systems.
    If system_id is provided, it will return the health status for that specific system.

    Args:
        system_id: System ID obtained from redfish_get_system_info tool (optional)

    Returns:
        HealthStatusResponse: System health status and chassis information

    Raises:
        ConfigurationError: If Redfish connection is not configured
        OperationError: If the operation fails

    Example:
        To get health status for all systems:
        redfish_get_health_status()

        To get health status for system with ID "1":
        redfish_get_health_status(system_id="1")
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

    # Strip whitespace from system_id
    if system_id:
        system_id = system_id.strip()

    try:
        if system_id:
            # Get health status for a specific system
            logger.info(f"Getting health status for system {system_id}")

            system_data = redfish_client.get(f"/redfish/v1/Systems/{system_id}")

            # For single system, include system ID in health status and no chassis data
            system_health_with_id = {
                "system_id": system_id,
                "system_name": system_data.get("Name", "Unknown"),
                **system_data.get("Status", {})
            }

            health_response = HealthStatusResponse(
                system_health=system_health_with_id,
                power_state=system_data.get("PowerState"),
                chassis=[]  # No chassis data for single system queries
            )

            logger.info(f"Retrieved health status for system {system_id}")
            return health_response
        else:
            # Get health status for all systems
            logger.info("Getting health status for all systems")

            # Fetch all systems data first
            systems_data = redfish_client.get("/redfish/v1/Systems/")
            all_systems_health = []

            # Fetch chassis data once to avoid repetition
            chassis_data = redfish_client.get("/redfish/v1/Chassis/")
            all_chassis = []

            # Build chassis list once
            for chassis_url in chassis_data.get("Members", []):
                try:
                    chassis_info = redfish_client.get(chassis_url["@odata.id"])
                    chassis_health = ChassisHealth(
                        name=chassis_info.get("Name"),
                        status=chassis_info.get("Status", {}),
                        power_state=chassis_info.get("PowerState")
                    )
                    all_chassis.append(chassis_health)
                except Exception as e:
                    logger.warning(f"Failed to get chassis info: {e}")
                    continue

            # Now process each system
            for system_url in systems_data.get("Members", []):
                try:
                    system_data = redfish_client.get(system_url["@odata.id"])
                    system_id = system_data.get("Id", "Unknown")

                    # Create health response for this system (without chassis to avoid duplication)
                    system_health = HealthStatusResponse(
                        system_health=system_data.get("Status", {}),
                        power_state=system_data.get("PowerState"),
                        chassis=[]  # Empty chassis list for individual systems
                    )

                    all_systems_health.append({
                        "system_id": system_id,
                        "system_name": system_data.get("Name", "Unknown"),
                        "health": system_health
                    })

                except Exception as e:
                    logger.warning(f"Failed to get health status for system {system_id}: {e}")
                    # Continue with other systems
                    continue

            if all_systems_health:
                # Create a comprehensive response with all systems and chassis
                # Include system IDs in the summary for better clarity
                system_ids = [sys["system_id"] for sys in all_systems_health]
                system_names = [sys["system_name"] for sys in all_systems_health]

                comprehensive_health = HealthStatusResponse(
                    system_health={
                        "summary": f"Health status for {len(all_systems_health)} systems",
                        "system_ids": system_ids,
                        "system_names": system_names
                    },
                    power_state="Multiple",  # Indicate multiple systems
                    chassis=all_chassis  # Use the chassis list we built once
                )

                logger.info(f"Retrieved health status for {len(all_systems_health)} systems with {len(all_chassis)} chassis")
                return comprehensive_health
            else:
                return HealthStatusResponse(
                    system_health={"summary": "No systems found"},
                    power_state="None",
                    chassis=[]
                )

    except Exception as e:
        if system_id:
            error_msg = f"Error getting health status for system {system_id}: {str(e)}"
        else:
            error_msg = f"Error getting health status for all systems: {str(e)}"

        logger.error(error_msg)
        raise OperationError(error_msg)


def redfish_get_sensors(
    system_id: str,
    sensor_type: str = "All"
) -> SensorsResponse:
    """
    Get sensor readings (temperature, fans, power, etc.) for a specific system.

    This tool provides real-time sensor data including:
    - Temperature sensor readings
    - Fan speed and status
    - Power supply information
    - Voltage readings

    Args:
        system_id: System ID obtained from redfish_get_system_info tool
        sensor_type: Type of sensors to retrieve. Must be one of:
                    "Temperature", "Fan", "All"

    Returns:
        SensorsResponse: Sensor readings organized by chassis

    Raises:
        ConfigurationError: If Redfish connection is not configured
        ValidationError: If the sensor type is invalid
        OperationError: If the operation fails

    Example:
        To get all sensor data for system with ID "1":
        redfish_get_sensors(system_id="1", sensor_type="All")

        To get only temperature sensors:
        redfish_get_sensors(system_id="1", sensor_type="Temperature")
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

    # Validate sensor type
    valid_sensor_types = ["Temperature", "Fan", "All"]
    if sensor_type not in valid_sensor_types:
        raise ValidationError(f"Invalid sensor type '{sensor_type}'. Must be one of: {valid_sensor_types}")

    try:
        logger.info(f"Getting {sensor_type} sensors for system {system_id}")

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

                # Filter sensor data based on sensor_type
                sensor_data = {}

                if sensor_type in ["Temperature", "All"]:
                    sensor_data["Temperatures"] = thermal_data.get("Temperatures", [])

                if sensor_type in ["Fan", "All"]:
                    sensor_data["Fans"] = thermal_data.get("Fans", [])

            except Exception as e:
                sensor_data = {"error": f"Sensor data not available: {str(e)}"}

            sensor_response = SensorDataResponse(
                chassis_name=chassis_name,
                data=sensor_data
            )
            sensor_list.append(sensor_response)

        sensors_response = SensorsResponse(
            sensor_type=sensor_type,
            sensors=sensor_list
        )

        logger.info(f"Retrieved {sensor_type} sensors for system {system_id} from {len(sensor_list)} chassis")
        return sensors_response

    except Exception as e:
        logger.error(f"Error getting sensors for system {system_id}: {e}")
        raise


def redfish_get_firmware_inventory(system_id: str = None) -> dict:
    """
    Get firmware inventory information for systems.

    This tool provides comprehensive firmware information including:
    - BIOS version and update status
    - BMC firmware version
    - Drive firmware versions
    - Network adapter firmware
    - Overall firmware health status

    Args:
        system_id: System ID obtained from redfish_get_system_info tool (optional)
                   If not provided, returns firmware info for all systems

    Returns:
        dict: Firmware inventory information

    Raises:
        ConfigurationError: If Redfish connection is not configured
        OperationError: If the operation fails

    Example:
        To get firmware info for all systems:
        redfish_get_firmware_inventory()

        To get firmware info for system with ID "1":
        redfish_get_firmware_inventory(system_id="1")
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

    # Strip whitespace from system_id
    if system_id:
        system_id = system_id.strip()

    try:
        if system_id:
            # Get firmware info for a specific system
            logger.info(f"Getting firmware inventory for system {system_id}")

            # Get system firmware inventory
            try:
                firmware_data = redfish_client.get(f"/redfish/v1/Systems/{system_id}/FirmwareInventory")
            except Exception as e:
                firmware_data = {"error": f"Could not retrieve firmware inventory: {str(e)}"}

            # Get BIOS information
            try:
                bios_data = redfish_client.get(f"/redfish/v1/Systems/{system_id}/Bios")
            except Exception as e:
                bios_data = {"error": f"Could not retrieve BIOS info: {str(e)}"}

            # Get manager firmware info
            try:
                manager_data = redfish_client.get("/redfish/v1/Managers/")
                manager_firmware = []
                for manager_url in manager_data.get("Members", []):
                    manager_info = redfish_client.get(manager_url["@odata.id"])
                    manager_firmware.append({
                        "id": manager_info.get("Id"),
                        "name": manager_info.get("Name"),
                        "firmware_version": manager_info.get("FirmwareVersion"),
                        "status": manager_info.get("Status", {})
                    })
            except Exception as e:
                manager_firmware = {"error": f"Could not retrieve manager firmware: {str(e)}"}

            firmware_info = {
                "system_id": system_id,
                "firmware_inventory": firmware_data,
                "bios": bios_data,
                "managers": manager_firmware,
                "timestamp": "now"
            }

            logger.info(f"Retrieved firmware inventory for system {system_id}")
            return firmware_info

        else:
            # Get firmware info for all systems
            logger.info("Getting firmware inventory for all systems")

            systems_data = redfish_client.get("/redfish/v1/Systems/")
            all_firmware_info = []

            for system_url in systems_data.get("Members", []):
                try:
                    system_data = redfish_client.get(system_url["@odata.id"])
                    system_id = system_data.get("Id", "Unknown")

                    # Get firmware inventory for this system
                    try:
                        firmware_data = redfish_client.get(f"/redfish/v1/Systems/{system_id}/FirmwareInventory")
                    except Exception as e:
                        firmware_data = {"error": f"Could not retrieve firmware inventory: {str(e)}"}

                    # Get BIOS info
                    try:
                        bios_data = redfish_client.get(f"/redfish/v1/Systems/{system_id}/Bios")
                    except Exception as e:
                        bios_data = {"error": f"Could not retrieve BIOS info: {str(e)}"}

                    system_firmware = {
                        "system_id": system_id,
                        "system_name": system_data.get("Name", "Unknown"),
                        "firmware_inventory": firmware_data,
                        "bios": bios_data
                    }

                    all_firmware_info.append(system_firmware)

                except Exception as e:
                    logger.warning(f"Failed to get firmware info for system {system_id}: {e}")
                    continue

            # Get manager firmware info once
            try:
                manager_data = redfish_client.get("/redfish/v1/Managers/")
                manager_firmware = []
                for manager_url in manager_data.get("Members", []):
                    manager_info = redfish_client.get(manager_url["@odata.id"])
                    manager_firmware.append({
                        "id": manager_info.get("Id"),
                        "name": manager_info.get("Name"),
                        "firmware_version": manager_info.get("FirmwareVersion"),
                        "status": manager_info.get("Status", {})
                    })
            except Exception as e:
                manager_firmware = {"error": f"Could not retrieve manager firmware: {str(e)}"}

            comprehensive_firmware = {
                "summary": f"Firmware inventory for {len(all_firmware_info)} systems",
                "systems": all_firmware_info,
                "managers": manager_firmware,
                "timestamp": "now"
            }

            logger.info(f"Retrieved firmware inventory for {len(all_firmware_info)} systems")
            return comprehensive_firmware

    except Exception as e:
        if system_id:
            error_msg = f"Error getting firmware inventory for system {system_id}: {str(e)}"
        else:
            error_msg = f"Error getting firmware inventory for all systems: {str(e)}"

        logger.error(error_msg)
        raise OperationError(error_msg)


def redfish_get_power_consumption(system_id: str = None) -> dict:
    """
    Get power consumption and efficiency metrics for systems.

    This tool provides real-time power usage information including:
    - Current power consumption (watts)
    - Power efficiency metrics
    - Power supply status and health
    - Historical power trends
    - Power capping information

    Args:
        system_id: System ID obtained from redfish_get_system_info tool (optional)
                   If not provided, returns power info for all systems

    Returns:
        dict: Power consumption and efficiency information

    Raises:
        ConfigurationError: If Redfish connection is not configured
        OperationError: If the operation fails

    Example:
        To get power consumption for all systems:
        redfish_get_power_consumption()

        To get power consumption for system with ID "1":
        redfish_get_power_consumption(system_id="1")
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

    # Strip whitespace from system_id
    if system_id:
        system_id = system_id.strip()

    try:
        if system_id:
            # Get power info for a specific system
            logger.info(f"Getting power consumption for system {system_id}")

            # Get system power information
            try:
                power_data = redfish_client.get(f"/redfish/v1/Systems/{system_id}")
            except Exception as e:
                power_data = {"error": f"Could not retrieve system power info: {str(e)}"}

            # Get chassis power information
            try:
                chassis_data = redfish_client.get("/redfish/v1/Chassis/")
                chassis_power = []
                for chassis_url in chassis_data.get("Members", []):
                    chassis_info = redfish_client.get(chassis_url["@odata.id"])
                    chassis_power.append({
                        "id": chassis_info.get("Id"),
                        "name": chassis_info.get("Name"),
                        "power_state": chassis_info.get("PowerState"),
                        "power_consumption_watts": chassis_info.get("PowerConsumptionWatts"),
                        "status": chassis_info.get("Status", {})
                    })
            except Exception as e:
                chassis_power = {"error": f"Could not retrieve chassis power info: {str(e)}"}

            # Get power supply information
            try:
                power_supplies = redfish_client.get(f"/redfish/v1/Chassis/1/Power")
                power_supply_info = power_supplies.get("PowerSupplies", [])
            except Exception as e:
                power_supply_info = {"error": f"Could not retrieve power supply info: {str(e)}"}

            power_info = {
                "system_id": system_id,
                "system_power": power_data,
                "chassis_power": chassis_power,
                "power_supplies": power_supply_info,
                "timestamp": "now"
            }

            logger.info(f"Retrieved power consumption for system {system_id}")
            return power_info

        else:
            # Get power info for all systems
            logger.info("Getting power consumption for all systems")

            systems_data = redfish_client.get("/redfish/v1/Systems/")
            all_power_info = []

            for system_url in systems_data.get("Members", []):
                try:
                    system_data = redfish_client.get(system_url["@odata.id"])
                    system_id = system_data.get("Id", "Unknown")

                    # Get power info for this system
                    try:
                        power_data = redfish_client.get(f"/redfish/v1/Systems/{system_id}")
                    except Exception as e:
                        power_data = {"error": f"Could not retrieve system power info: {str(e)}"}

                    system_power = {
                        "system_id": system_id,
                        "system_name": system_data.get("Name", "Unknown"),
                        "power_state": system_data.get("PowerState"),
                        "power_consumption_watts": system_data.get("PowerConsumptionWatts"),
                        "power_info": power_data
                    }

                    all_power_info.append(system_power)

                except Exception as e:
                    logger.warning(f"Failed to get power info for system {system_id}: {e}")
                    continue

            # Get overall chassis power information
            try:
                chassis_data = redfish_client.get("/redfish/v1/Chassis/")
                chassis_power = []
                for chassis_url in chassis_data.get("Members", []):
                    chassis_info = redfish_client.get(chassis_url["@odata.id"])
                    chassis_power.append({
                        "id": chassis_info.get("Id"),
                        "name": chassis_info.get("Name"),
                        "power_state": chassis_info.get("PowerState"),
                        "power_consumption_watts": chassis_info.get("PowerConsumptionWatts"),
                        "status": chassis_info.get("Status", {})
                    })
            except Exception as e:
                chassis_power = {"error": f"Could not retrieve chassis power info: {str(e)}"}

            comprehensive_power = {
                "summary": f"Power consumption for {len(all_power_info)} systems",
                "systems": all_power_info,
                "chassis": chassis_power,
                "total_power_watts": sum(sys.get("power_consumption_watts", 0) for sys in all_power_info if sys.get("power_consumption_watts")),
                "timestamp": "now"
            }

            logger.info(f"Retrieved power consumption for {len(all_power_info)} systems")
            return comprehensive_power

    except Exception as e:
        if system_id:
            error_msg = f"Error getting power consumption for system {system_id}: {str(e)}"
        else:
            error_msg = f"Error getting power consumption for all systems: {str(e)}"

        logger.error(error_msg)
        raise OperationError(error_msg)
