"""Custom exceptions for the Redfish MCP server."""


class RedfishError(Exception):
    """Base exception for Redfish MCP server errors."""
    pass


class ConnectionError(RedfishError):
    """Raised when there's an issue connecting to Redfish endpoints."""
    pass


class ValidationError(RedfishError):
    """Raised when input validation fails."""
    pass


class AuthenticationError(RedfishError):
    """Raised when authentication fails."""
    pass


class ConfigurationError(RedfishError):
    """Raised when there's a configuration issue."""
    pass


class OperationError(RedfishError):
    """Raised when a Redfish operation fails."""
    pass
