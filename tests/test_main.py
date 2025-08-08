"""
Tests for the Redfish MCP server.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from unittest.mock import Mock, patch
from main import RedfishClient, RedfishConfig


def test_redfish_config():
    """Test RedfishConfig model."""
    config = RedfishConfig(
        host="https://192.168.1.100",
        username="admin",
        password="password123"
    )
    assert config.host == "https://192.168.1.100"
    assert config.username == "admin"
    assert config.password == "password123"
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


if __name__ == "__main__":
    pytest.main([__file__])
