"""
Tests for the Redfish MCP server.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from unittest.mock import Mock, MagicMock, patch
from redfish_mcp_server.client.redfish_client import RedfishClient
from redfish_mcp_server.config.models import RedfishConfig


def test_redfish_config():
    """Test RedfishConfig model."""
    config = RedfishConfig(
        host="https://192.168.1.100",
        username="admin",
        password="password123"
    )
    assert config.host == "https://192.168.1.100"
    assert config.username == "admin"
    assert config.password.get_secret_value() == "password123"
    assert config.verify_ssl is False
    assert config.timeout == 30


def test_redfish_client_initialization():
    """Test RedfishClient initialization."""
    config = RedfishConfig(
        host="https://192.168.1.100",
        username="admin",
        password="password123"
    )
    client = RedfishClient(config)

    assert client.config == config
    assert client.base_url == "https://192.168.1.100"
    assert client.timeout == 30


from pydantic import SecretStr
from redfish_mcp_server.utils.exceptions import AuthenticationError, ConnectionError


def test_client_session_auth_login():
    """Test client uses session auth by default."""
    config = RedfishConfig(
        host="https://192.168.100.23",
        username="admin",
        password="password123",
        auth_method="session",
    )
    with patch("redfish_mcp_server.client.redfish_client.redfish_client") as mock_rf:
        mock_obj = MagicMock()
        mock_rf.return_value = mock_obj

        client = RedfishClient(config)
        client._login()

        mock_rf.assert_called_once()
        mock_obj.login.assert_called_once_with(auth="session")


def test_client_basic_auth_fallback():
    """Test client falls back to basic auth if session auth fails."""
    config = RedfishConfig(
        host="https://192.168.100.23",
        username="admin",
        password="password123",
        auth_method="session",
    )
    with patch("redfish_mcp_server.client.redfish_client.redfish_client") as mock_rf:
        mock_obj = MagicMock()
        mock_rf.return_value = mock_obj
        # Session auth fails
        mock_obj.login.side_effect = [Exception("SessionService not found"), None]

        client = RedfishClient(config)
        client._login()

        assert mock_obj.login.call_count == 2
        mock_obj.login.assert_called_with(auth="basic")


def test_client_close_calls_logout():
    """Test close() calls logout on the DMTF client."""
    config = RedfishConfig(
        host="https://192.168.100.23",
        username="admin",
        password="password123",
    )
    with patch("redfish_mcp_server.client.redfish_client.redfish_client") as mock_rf:
        mock_obj = MagicMock()
        mock_rf.return_value = mock_obj

        client = RedfishClient(config)
        client._client = mock_obj
        client.close()

        mock_obj.logout.assert_called_once()


def test_client_get_delegates_to_dmtf():
    """Test get() delegates to DMTF client and returns dict."""
    config = RedfishConfig(
        host="https://192.168.100.23",
        username="admin",
        password="password123",
    )
    with patch("redfish_mcp_server.client.redfish_client.redfish_client") as mock_rf:
        mock_obj = MagicMock()
        mock_rf.return_value = mock_obj

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.dict = {"Id": "1", "Name": "System"}
        mock_obj.get.return_value = mock_response

        client = RedfishClient(config)
        client._client = mock_obj
        result = client.get("/redfish/v1/Systems/1")

        mock_obj.get.assert_called_once_with("/redfish/v1/Systems/1")
        assert result == {"Id": "1", "Name": "System"}

def test_redfish_config_secret_str():
    """Test RedfishConfig uses SecretStr for password."""
    config = RedfishConfig(
        host="https://192.168.1.100",
        username="admin",
        password="password123"
    )
    assert isinstance(config.password, SecretStr)
    assert config.password.get_secret_value() == "password123"
    assert "password123" not in repr(config)
    assert "password123" not in config.model_dump_json()


def test_redfish_config_new_fields():
    """Test new auth_method, bmc_vendor, and mTLS fields."""
    config = RedfishConfig(
        host="https://192.168.1.100",
        username="admin",
        password="password123"
    )
    assert config.auth_method == "session"
    assert config.bmc_vendor == "asrockrack"
    assert config.client_cert is None
    assert config.client_key is None
    assert config.ca_bundle is None


def test_redfish_config_mtls_fields():
    """Test mTLS fields accept values for phase 2."""
    config = RedfishConfig(
        host="https://192.168.1.100",
        username="admin",
        password="password123",
        client_cert="/path/to/cert.pem",
        client_key="/path/to/key.pem",
        ca_bundle="/path/to/ca.pem",
    )
    assert config.client_cert == "/path/to/cert.pem"
    assert isinstance(config.client_key, SecretStr)
    assert config.ca_bundle == "/path/to/ca.pem"


if __name__ == "__main__":
    pytest.main([__file__])
