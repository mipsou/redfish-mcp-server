"""Management tools for users, logs, and configuration."""

import logging
import os
from typing import Union



from ..config.models import (
    UserAccountsResponse, UserAccount, EventLogsResponse, LogEntry,
    ClearLogsResult, ConnectionResult, ConfigStatusResponse
)
from ..utils.exceptions import ConfigurationError, ValidationError

logger = logging.getLogger(__name__)

# Global client instance - will be set by main module
redfish_client = None


def set_client(client):
    """Set the global Redfish client instance."""
    global redfish_client
    redfish_client = client


def redfish_manage_users(action: str) -> Union[UserAccountsResponse, dict]:
    """
    Manage user accounts on the Redfish system.

    This tool provides user account management capabilities including:
    - List all user accounts
    - View account details (username, role, enabled status, locked status)

    Args:
        action: User management action. Currently supports:
                "list" - List all user accounts

    Returns:
        UserAccountsResponse: List of user accounts when action is "list"
        dict: Status message for unsupported actions

    Raises:
        ConfigurationError: If Redfish connection is not configured
        OperationError: If the operation fails

    Example:
        To list all user accounts:
        redfish_manage_users(action="list")
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

    if action == "list":
        try:
            logger.info("Retrieving user accounts")

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

            logger.info(f"Retrieved {len(user_list)} user accounts")
            return UserAccountsResponse(accounts=user_list)

        except Exception as e:
            logger.error(f"Error getting user accounts: {e}")
            raise
    else:
        return {"message": f"User management action '{action}' is not yet implemented"}


def redfish_get_manager_logs(
    manager_id: str,
    limit: int = 50
) -> EventLogsResponse:
    """
    Retrieve manager event logs.

    This tool provides access to manager event logs including:
    - System events and alerts
    - Error messages and warnings
    - Informational messages
    - Timestamps and severity levels

    Args:
        manager_id: ID of the manager to retrieve logs from, obtained from redfish_get_manager_info tool
        limit: Maximum number of log entries to retrieve (default: 50, max: 100)

    Returns:
        EventLogsResponse: Manager event logs with entry details

    Raises:
        ConfigurationError: If Redfish connection is not configured
        ValidationError: If the limit is invalid
        OperationError: If the operation fails

    Example:
        To get the last 25 manager logs:
        redfish_get_manager_logs(manager_id="1", limit=25)
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

    # Validate limit
    if limit <= 0 or limit > 100:
        raise ValidationError("Limit must be between 1 and 100")

    try:
        logger.info(f"Retrieving manager logs for manager {manager_id} (limit: {limit})")

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

        logger.info(f"Retrieved {len(log_entries)} log entries for manager {manager_id}")
        return EventLogsResponse(
            log_type="Manager",
            entries=log_entries,
            count=len(log_entries)
        )

    except Exception as e:
        logger.error(f"Error getting event logs for manager {manager_id}: {e}")
        raise


def redfish_clear_logs(log_type: str = "System") -> ClearLogsResult:
    """
    Clear system event logs.

    This tool allows clearing of various log types to free up storage space:
    - System logs: General system events and alerts
    - Security logs: Authentication and authorization events
    - Manager logs: BMC management events

    Args:
        log_type: Type of log to clear. Must be one of:
                  "System", "Security", "Manager"

    Returns:
        ClearLogsResult: Result of the log clearing operation

    Raises:
        ConfigurationError: If Redfish connection is not configured
        ValidationError: If the log type is invalid
        OperationError: If the operation fails

    Example:
        To clear system logs:
        redfish_clear_logs(log_type="System")
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

    # Validate log type
    valid_log_types = ["System", "Security", "Manager"]
    if log_type not in valid_log_types:
        raise ValidationError(f"Invalid log type '{log_type}'. Must be one of: {valid_log_types}")

    try:
        logger.info(f"Clearing {log_type} logs")

        clear_data = {}
        redfish_client.post(f"/redfish/v1/Managers/1/LogServices/{log_type}/Actions/LogService.ClearLog", clear_data)

        logger.info(f"{log_type} logs cleared successfully")
        return ClearLogsResult(
            success=True,
            message=f"{log_type} logs cleared successfully",
            log_type=log_type
        )

    except Exception as e:
        error_msg = f"Failed to clear {log_type} logs: {str(e)}"
        logger.error(error_msg)
        return ClearLogsResult(
            success=False,
            message=error_msg,
            log_type=log_type
        )


def redfish_configure(
    host: str,
    username: str,
    password: str,
    verify_ssl: bool = False
) -> ConnectionResult:
    """
    Configure Redfish connection parameters and test the connection.

    This tool allows manual configuration of Redfish connection settings:
    - Host URL (must include protocol, e.g., https://192.168.1.100)
    - Username and password for authentication
    - SSL verification settings

    Args:
        host: Redfish host URL (e.g., "https://192.168.1.100")
        username: Username for authentication
        password: Password for authentication
        verify_ssl: Whether to verify SSL certificates (default: False)

    Returns:
        ConnectionResult: Result of the connection test

    Raises:
        ConfigurationError: If configuration fails
        ConnectionError: If connection test fails

    Example:
        To configure connection to a BMC:
        redfish_configure(
            host="https://192.168.1.100",
            username="admin",
            password="password123",
            verify_ssl=False
        )
    """
    from ..client.redfish_client import RedfishClient
    from ..config.models import RedfishConfig

    global redfish_client

    try:
        logger.info(f"Configuring Redfish connection to {host}")

        config = RedfishConfig(
            host=host,
            username=username,
            password=password,
            verify_ssl=verify_ssl
        )
        redfish_client = RedfishClient(config)

        # Test connection
        try:
            service_root = redfish_client.test_connection()
            logger.info(f"Successfully connected to Redfish service at {host}")

            return ConnectionResult(
                success=True,
                message="Successfully connected to Redfish service",
                service_name=service_root.get('Name', 'Unknown'),
                version=service_root.get('RedfishVersion', 'Unknown'),
                uuid=service_root.get('UUID', 'Unknown')
            )

        except Exception as e:
            error_msg = f"Failed to connect to Redfish service: {str(e)}"
            logger.error(error_msg)
            return ConnectionResult(
                success=False,
                message=error_msg
            )

    except Exception as e:
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        return ConnectionResult(
            success=False,
            message=error_msg
        )


def redfish_get_config_status() -> ConfigStatusResponse:
    """
    Get current Redfish configuration status.

    This tool provides information about the current Redfish configuration:
    - Whether a connection is configured
    - Source of configuration (environment or manual)
    - Connection status and service information
    - Current connection parameters

    Returns:
        ConfigStatusResponse: Current configuration status and details

    Example:
        To check configuration status:
        redfish_get_config_status()
    """
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
        service_root = redfish_client.test_connection()
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


def redfish_get_security_status() -> dict:
    """
    Get security status and compliance information for the Redfish system.

    This tool provides comprehensive security assessment including:
    - TLS/SSL certificate status and expiration
    - Authentication methods and security policies
    - User account security status
    - Network security configuration
    - Compliance status and recommendations

    Returns:
        dict: Security status and compliance information

    Raises:
        ConfigurationError: If Redfish connection is not configured
        OperationError: If the operation fails

    Example:
        To get security status:
        redfish_get_security_status()
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

    try:
        logger.info("Getting security status and compliance information")

        security_info = {}

        # Get account service security information
        try:
            account_service = redfish_client.get("/redfish/v1/AccountService")
            security_info["account_service"] = {
                "auth_failure_logging_threshold": account_service.get("AuthFailureLoggingThreshold"),
                "account_lockout_threshold": account_service.get("AccountLockoutThreshold"),
                "account_lockout_duration": account_service.get("AccountLockoutDuration"),
                "account_lockout_counter_reset_after": account_service.get("AccountLockoutCounterResetAfter"),
                "min_password_length": account_service.get("MinPasswordLength"),
                "max_password_length": account_service.get("MaxPasswordLength"),
                "password_complexity": account_service.get("PasswordComplexity"),
                "password_expiration": account_service.get("PasswordExpiration")
            }
        except Exception as e:
            security_info["account_service"] = {"error": f"Could not retrieve account service info: {str(e)}"}

        # Get session service information
        try:
            session_service = redfish_client.get("/redfish/v1/SessionService")
            security_info["session_service"] = {
                "session_timeout": session_service.get("SessionTimeout"),
                "session_authentication": session_service.get("SessionAuthentication"),
                "session_creation_time": session_service.get("SessionCreationTime")
            }
        except Exception as e:
            security_info["session_service"] = {"error": f"Could not retrieve session service info: {str(e)}"}

        # Get user accounts and their security status
        try:
            accounts = redfish_client.get("/redfish/v1/AccountService/Accounts/")
            user_security = []
            for account_url in accounts.get("Members", []):
                account_data = redfish_client.get(account_url["@odata.id"])
                user_security.append({
                    "username": account_data.get("UserName"),
                    "role_id": account_data.get("RoleId"),
                    "enabled": account_data.get("Enabled"),
                    "locked": account_data.get("Locked"),
                    "password_change_required": account_data.get("PasswordChangeRequired"),
                    "last_login_time": account_data.get("LastLoginTime")
                })
            security_info["user_security"] = user_security
        except Exception as e:
            security_info["user_security"] = {"error": f"Could not retrieve user security info: {str(e)}"}

        # Get manager security information
        try:
            managers_data = redfish_client.get("/redfish/v1/Managers/")
            manager_security = []
            for manager_url in managers_data.get("Members", []):
                manager_info = redfish_client.get(manager_url["@odata.id"])
                manager_security.append({
                    "id": manager_info.get("Id"),
                    "name": manager_info.get("Name"),
                    "firmware_version": manager_info.get("FirmwareVersion"),
                    "status": manager_info.get("Status", {}),
                    "ethernet_interfaces": manager_info.get("EthernetInterfaces", {})
                })
            security_info["manager_security"] = manager_security
        except Exception as e:
            security_info["manager_security"] = {"error": f"Could not retrieve manager security info: {str(e)}"}

        # Get network security information
        try:
            # Try to get network protocol information
            network_protocols = redfish_client.get("/redfish/v1/Managers/1/NetworkProtocol")
            security_info["network_protocols"] = {
                "http_enabled": network_protocols.get("HTTP", {}).get("ProtocolEnabled"),
                "https_enabled": network_protocols.get("HTTPS", {}).get("ProtocolEnabled"),
                "ipmi_enabled": network_protocols.get("IPMI", {}).get("ProtocolEnabled"),
                "ssh_enabled": network_protocols.get("SSH", {}).get("ProtocolEnabled"),
                "telnet_enabled": network_protocols.get("Telnet", {}).get("ProtocolEnabled")
            }
        except Exception as e:
            security_info["network_protocols"] = {"error": f"Could not retrieve network protocol info: {str(e)}"}

        # Add timestamp and summary
        security_info["timestamp"] = "now"
        security_info["summary"] = "Security status and compliance assessment"

        # Add security recommendations
        security_recommendations = []

        # Check for common security issues
        if security_info.get("account_service", {}).get("account_lockout_threshold") == 0:
            security_recommendations.append("Account lockout threshold is disabled - consider enabling")

        if security_info.get("account_service", {}).get("min_password_length", 0) < 8:
            security_recommendations.append("Minimum password length is less than 8 characters")

        if security_info.get("network_protocols", {}).get("http_enabled"):
            security_recommendations.append("HTTP is enabled - consider disabling for HTTPS only")

        if security_info.get("network_protocols", {}).get("telnet_enabled"):
            security_recommendations.append("Telnet is enabled - consider disabling for SSH only")

        # Check for locked accounts
        locked_accounts = [user for user in security_info.get("user_security", []) if user.get("locked")]
        if locked_accounts:
            security_recommendations.append(f"Found {len(locked_accounts)} locked user accounts")

        security_info["security_recommendations"] = security_recommendations
        security_info["overall_security_score"] = max(0, 100 - len(security_recommendations) * 10)

        logger.info("Retrieved security status and compliance information")
        return security_info

    except Exception as e:
        error_msg = f"Error getting security status: {str(e)}"
        logger.error(error_msg)
        raise OperationError(error_msg)


def redfish_get_audit_logs(log_type: str = "All", limit: int = 100) -> dict:
    """
    Get comprehensive audit logs for security and compliance monitoring.

    This tool provides detailed audit trail information including:
    - User authentication events
    - System configuration changes
    - Security policy modifications
    - Access control changes
    - Compliance audit trails

    Args:
        log_type: Type of audit logs to retrieve. Must be one of:
                  "All", "Security", "System", "Configuration", "Access"
        limit: Maximum number of log entries to return (default: 100)

    Returns:
        dict: Audit log information

    Raises:
        ConfigurationError: If Redfish connection is not configured
        ValidationError: If the log type is invalid
        OperationError: If the operation fails

    Example:
        To get all audit logs:
        redfish_get_audit_logs()

        To get security audit logs with limit:
        redfish_get_audit_logs(log_type="Security", limit=50)
    """
    if not redfish_client:
        raise ConfigurationError("Please configure Redfish connection first using redfish_configure tool.")

    # Validate log type
    valid_log_types = ["All", "Security", "System", "Configuration", "Access"]
    if log_type not in valid_log_types:
        raise ValidationError(f"Invalid log type '{log_type}'. Must be one of: {valid_log_types}")

    try:
        logger.info(f"Getting {log_type} audit logs (limit: {limit})")

        audit_logs = {}

        # Get system event logs
        try:
            system_logs = redfish_client.get("/redfish/v1/Systems/1/LogServices/System/Entries")
            system_entries = system_logs.get("Members", [])[:limit]
            audit_logs["system_logs"] = {
                "count": len(system_entries),
                "entries": system_entries
            }
        except Exception as e:
            audit_logs["system_logs"] = {"error": f"Could not retrieve system logs: {str(e)}"}

        # Get manager event logs
        try:
            manager_logs = redfish_client.get("/redfish/v1/Managers/1/LogServices/Manager/Entries")
            manager_entries = manager_logs.get("Members", [])[:limit]
            audit_logs["manager_logs"] = {
                "count": len(manager_entries),
                "entries": manager_entries
            }
        except Exception as e:
            audit_logs["manager_logs"] = {"error": f"Could not retrieve manager logs: {str(e)}"}

        # Get security logs if available
        if log_type in ["All", "Security"]:
            try:
                security_logs = redfish_client.get("/redfish/v1/Managers/1/LogServices/Security/Entries")
                security_entries = security_logs.get("Members", [])[:limit]
                audit_logs["security_logs"] = {
                    "count": len(security_entries),
                    "entries": security_entries
                }
            except Exception as e:
                audit_logs["security_logs"] = {"error": f"Could not retrieve security logs: {str(e)}"}

        # Get configuration logs if available
        if log_type in ["All", "Configuration"]:
            try:
                # Look for configuration change events in system logs
                config_events = []
                for entry in audit_logs.get("system_logs", {}).get("entries", []):
                    if any(keyword in str(entry).lower() for keyword in ["config", "setting", "parameter", "change"]):
                        config_events.append(entry)

                audit_logs["configuration_logs"] = {
                    "count": len(config_events),
                    "entries": config_events
                }
            except Exception as e:
                audit_logs["configuration_logs"] = {"error": f"Could not retrieve configuration logs: {str(e)}"}

        # Get access control logs if available
        if log_type in ["All", "Access"]:
            try:
                # Look for access control events in security and manager logs
                access_events = []
                for log_source in ["security_logs", "manager_logs"]:
                    for entry in audit_logs.get(log_source, {}).get("entries", []):
                        if any(keyword in str(entry).lower() for keyword in ["login", "logout", "auth", "access", "permission"]):
                            access_events.append(entry)

                audit_logs["access_logs"] = {
                    "count": len(access_events),
                    "entries": access_events
                }
            except Exception as e:
                audit_logs["access_logs"] = {"error": f"Could not retrieve access logs: {str(e)}"}

        # Add summary and metadata
        total_entries = sum(
            log_data.get("count", 0)
            for log_data in audit_logs.values()
            if isinstance(log_data, dict) and "count" in log_data
        )

        audit_logs["summary"] = f"Retrieved {total_entries} audit log entries across {len(audit_logs) - 2} log sources"
        audit_logs["log_type"] = log_type
        audit_logs["limit"] = limit
        audit_logs["timestamp"] = "now"

        logger.info(f"Retrieved {total_entries} audit log entries")
        return audit_logs

    except Exception as e:
        error_msg = f"Error getting audit logs: {str(e)}"
        logger.error(error_msg)
        raise OperationError(error_msg)
