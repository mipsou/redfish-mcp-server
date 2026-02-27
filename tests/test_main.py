"""
Tests for the Redfish MCP server.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from unittest.mock import Mock, patch
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


@patch('redfish_mcp_server.main.requests.Session')
def test_redfish_client_get_request(mock_session):
    """Test GET request method."""
    # Setup mock
    mock_response = Mock()
    mock_response.json.return_value = {"test": "data"}
    mock_response.content = True
    mock_session.return_value.request.return_value = mock_response

    config = RedfishConfig(
        host="https://192.168.1.100",
        username="admin",
        password="password123"
    )
    client = RedfishClient(config)

    result = client.get("/redfish/v1/")

    assert result == {"test": "data"}
    mock_session.return_value.request.assert_called_once()


from pydantic import SecretStr

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
