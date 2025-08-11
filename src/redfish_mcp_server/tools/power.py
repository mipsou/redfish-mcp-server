"""Power control tools for Redfish systems."""

import logging



from ..config.models import PowerControlResult
from ..utils.exceptions import ConfigurationError, ValidationError, OperationError

logger = logging.getLogger(__name__)

# Global client instance - will be set by main module
redfish_client = None


def set_client(client):
    """Set the global Redfish client instance."""
    global redfish_client
    redfish_client = client


def redfish_power_control(
    action: str,
    system_id: str
) -> PowerControlResult:
    """
    Control system power state.

    This tool allows you to perform various power operations on Redfish systems:
    - On: Power on the system
    - ForceOff: Force power off the system
    - GracefulShutdown: Gracefully shutdown the system
    - ForceRestart: Force restart the system
    - GracefulRestart: Gracefully restart the system

    Args:
        action: Power action to perform. Can be in any case (e.g., "on", "ON", "On", "forceOff", "forceoff", etc.).
                Valid actions: On, ForceOff, GracefulShutdown, ForceRestart, GracefulRestart
        system_id: System ID obtained from redfish_get_system_info tool

    Returns:
        PowerControlResult: Result of the power control operation

    Raises:
        ConfigurationError: If Redfish connection is not configured
        ValidationError: If the action is invalid
        OperationError: If the operation fails

    Example:
        To power on a system with ID "1":
        redfish_power_control(action="on", system_id="1")
        redfish_power_control(action="ON", system_id="1")
        redfish_power_control(action="On", system_id="1")
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

    # Validate power action (case-insensitive)
    valid_actions = ["On", "ForceOff", "GracefulShutdown", "ForceRestart", "GracefulRestart"]

    # Normalize the action to handle different case formats
    action_normalized = action.strip()
    action_matched = None

    # Try exact match first
    if action_normalized in valid_actions:
        action_matched = action_normalized
    else:
        # Try case-insensitive matching
        for valid_action in valid_actions:
            if action_normalized.lower() == valid_action.lower():
                action_matched = valid_action
                break

    if not action_matched:
        # Provide helpful suggestions for similar actions
        suggestions = []
        for valid_action in valid_actions:
            if action_normalized.lower() in valid_action.lower() or valid_action.lower() in action_normalized.lower():
                suggestions.append(valid_action)

        if suggestions:
            suggestion_text = f" Did you mean: {', '.join(suggestions)}?"
        else:
            suggestion_text = f" Valid actions are: {', '.join(valid_actions)}"

        raise ValidationError(f"Invalid action '{action}'.{suggestion_text}")

    # Validate system_id is not empty and strip whitespace
    if not system_id or not system_id.strip():
        raise ValidationError("System ID cannot be empty")
    system_id = system_id.strip()

    try:
        logger.info(f"Executing power action '{action_matched}' on system {system_id}")

        # First, verify the system exists by trying to get its information
        try:
            system_info = redfish_client.get(f"/redfish/v1/Systems/{system_id}")
            logger.debug(f"System {system_id} found: {system_info.get('Name', 'Unknown')}")
        except Exception as e:
            if "not found" in str(e).lower():
                return PowerControlResult(
                    success=False,
                    message=f"System '{system_id}' does not exist. Use redfish_get_system_info to see available systems.",
                    system_id=system_id,
                    action=action_matched
                )
            else:
                # Re-raise other errors
                raise

        # Execute the power action
        power_data = {"ResetType": action_matched}
        redfish_client.post(f"/redfish/v1/Systems/{system_id}/Actions/ComputerSystem.Reset", power_data)

        logger.info(f"Power action '{action_matched}' executed successfully on system {system_id}")
        return PowerControlResult(
            success=True,
            message=f"Power action '{action_matched}' executed successfully on system {system_id}",
            system_id=system_id,
            action=action_matched
        )

    except Exception as e:
        # Provide user-friendly error messages based on the exception type
        if "not found" in str(e).lower():
            error_msg = f"System '{system_id}' does not exist. Use redfish_get_system_info to see available systems."
        elif "authentication failed" in str(e).lower():
            error_msg = f"Authentication failed. Please check your username and password."
        elif "access denied" in str(e).lower():
            error_msg = f"Access denied. You don't have permission to perform power operations on system '{system_id}'."
        elif "timeout" in str(e).lower():
            error_msg = f"Request timeout. The Redfish service may be slow to respond."
        elif "connection failed" in str(e).lower():
            error_msg = f"Connection failed. Please check your network connection and Redfish host URL."
        else:
            error_msg = f"Failed to execute power action '{action_matched}' on system {system_id}: {str(e)}"

        logger.error(f"Power control error: {error_msg}")
        return PowerControlResult(
            success=False,
            message=error_msg,
            system_id=system_id,
            action=action_matched
        )
