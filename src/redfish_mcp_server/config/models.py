"""Pydantic models for Redfish MCP server configuration and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, SecretStr


class RedfishConfig(BaseModel):
    """Configuration for Redfish connection"""
    host: str = Field(..., description="Redfish host URL (https:// recommended)")
    username: str = Field(..., description="Username for authentication")
    password: SecretStr = Field(..., description="Password for authentication")
    verify_ssl: bool = Field(default=False, description="Verify SSL certificates")
    timeout: int = Field(default=60, description="Request timeout in seconds (AST2500 TLS handshake ~17s)")
    auth_method: str = Field(default="session", description="Auth method: 'session' or 'basic'")
    bmc_vendor: str = Field(default="asrockrack", description="BMC vendor (qualified: asrockrack)")
    # Ready for phase 2 — mTLS
    client_cert: Optional[str] = Field(default=None, description="Path to client certificate (.pem)")
    client_key: Optional[SecretStr] = Field(default=None, description="Path to client private key")
    ca_bundle: Optional[str] = Field(default=None, description="Path to CA bundle for SSL verification")


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
