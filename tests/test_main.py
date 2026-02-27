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
from redfish_mcp_server.utils.exceptions import AuthenticationError, ConnectionError, OperationError


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


def test_initialize_from_env_reads_auth_method(monkeypatch):
    """Test _initialize_from_env reads REDFISH_AUTH_METHOD."""
    monkeypatch.setenv("REDFISH_HOST", "https://192.168.100.23")
    monkeypatch.setenv("REDFISH_USERNAME", "admin")
    monkeypatch.setenv("REDFISH_PASSWORD", "pass")
    monkeypatch.setenv("REDFISH_AUTH_METHOD", "basic")
    monkeypatch.setenv("REDFISH_BMC_VENDOR", "supermicro")

    # We can't test full init without a BMC, but we can test config creation
    from redfish_mcp_server.config.models import RedfishConfig

    host = os.getenv("REDFISH_HOST")
    username = os.getenv("REDFISH_USERNAME")
    password = os.getenv("REDFISH_PASSWORD")
    auth_method = os.getenv("REDFISH_AUTH_METHOD", "session")
    bmc_vendor = os.getenv("REDFISH_BMC_VENDOR", "asrockrack")

    config = RedfishConfig(
        host=host,
        username=username,
        password=password,
        auth_method=auth_method,
        bmc_vendor=bmc_vendor,
    )
    assert config.auth_method == "basic"
    assert config.bmc_vendor == "supermicro"


def test_client_post_delegates_to_dmtf():
    """Test post() delegates to DMTF client."""
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
        mock_response.dict = {"success": True}
        mock_obj.post.return_value = mock_response

        client = RedfishClient(config)
        client._client = mock_obj
        result = client.post("/redfish/v1/Systems/1/Actions/ComputerSystem.Reset", data={"ResetType": "On"})

        mock_obj.post.assert_called_once_with("/redfish/v1/Systems/1/Actions/ComputerSystem.Reset", body={"ResetType": "On"})
        assert result == {"success": True}


def test_client_patch_delegates_to_dmtf():
    """Test patch() delegates to DMTF client."""
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
        mock_response.dict = {"updated": True}
        mock_obj.patch.return_value = mock_response

        client = RedfishClient(config)
        client._client = mock_obj
        result = client.patch("/redfish/v1/Systems/1", data={"AssetTag": "test"})

        mock_obj.patch.assert_called_once_with("/redfish/v1/Systems/1", body={"AssetTag": "test"})
        assert result == {"updated": True}


def test_client_delete_delegates_to_dmtf():
    """Test delete() delegates to DMTF client."""
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
        mock_response.dict = {}
        mock_obj.delete.return_value = mock_response

        client = RedfishClient(config)
        client._client = mock_obj
        result = client.delete("/redfish/v1/Sessions/1")

        mock_obj.delete.assert_called_once_with("/redfish/v1/Sessions/1")
        assert result == {}


def test_handle_response_403_raises_operation_error():
    """Test _handle_response raises OperationError on 403."""
    config = RedfishConfig(
        host="https://192.168.100.23",
        username="admin",
        password="password123",
    )
    client = RedfishClient(config)

    mock_response = MagicMock()
    mock_response.status = 403

    with pytest.raises(OperationError, match="Access denied"):
        client._handle_response(mock_response)


def test_handle_response_404_raises_operation_error():
    """Test _handle_response raises OperationError on 404."""
    config = RedfishConfig(
        host="https://192.168.100.23",
        username="admin",
        password="password123",
    )
    client = RedfishClient(config)

    mock_response = MagicMock()
    mock_response.status = 404
    mock_response.request.path = "/redfish/v1/Systems/99"

    with pytest.raises(OperationError, match="Resource not found"):
        client._handle_response(mock_response)


def test_handle_response_500_raises_operation_error():
    """Test _handle_response raises OperationError on 500."""
    config = RedfishConfig(
        host="https://192.168.100.23",
        username="admin",
        password="password123",
    )
    client = RedfishClient(config)

    mock_response = MagicMock()
    mock_response.status = 500

    with pytest.raises(OperationError, match="Server error"):
        client._handle_response(mock_response)


def test_handle_response_401_raises_auth_error():
    """Test _handle_response raises AuthenticationError on 401 and resets client."""
    config = RedfishConfig(
        host="https://192.168.100.23",
        username="admin",
        password="password123",
    )
    client = RedfishClient(config)
    client._client = MagicMock()  # simulate connected

    mock_response = MagicMock()
    mock_response.status = 401

    with pytest.raises(AuthenticationError, match="Token expired"):
        client._handle_response(mock_response)

    assert client._client is None  # client reset for reconnect


def test_security_warning_http(caplog):
    """Test warning logged for http:// connection."""
    import logging
    with caplog.at_level(logging.WARNING):
        config = RedfishConfig(
            host="http://192.168.100.23",
            username="admin",
            password="password123",
        )
        RedfishClient(config)

    assert "Unencrypted connection" in caplog.text


def test_security_warning_no_ssl_verify(caplog):
    """Test warning logged when verify_ssl is False."""
    import logging
    with caplog.at_level(logging.WARNING):
        config = RedfishConfig(
            host="https://192.168.100.23",
            username="admin",
            password="password123",
            verify_ssl=False,
        )
        RedfishClient(config)

    assert "SSL certificate not verified" in caplog.text


def test_security_warning_unknown_vendor(caplog):
    """Test warning logged for non-qualified BMC vendor."""
    import logging
    with caplog.at_level(logging.WARNING):
        config = RedfishConfig(
            host="https://192.168.100.23",
            username="admin",
            password="password123",
            bmc_vendor="supermicro",
        )
        RedfishClient(config)

    assert "qualified only for ASRock Rack" in caplog.text


def test_ensure_connected_calls_login_once():
    """Test _ensure_connected triggers login when _client is None."""
    config = RedfishConfig(
        host="https://192.168.100.23",
        username="admin",
        password="password123",
    )
    with patch("redfish_mcp_server.client.redfish_client.redfish_client") as mock_rf:
        mock_obj = MagicMock()
        mock_rf.return_value = mock_obj

        client = RedfishClient(config)
        assert client._client is None

        client._ensure_connected()
        assert client._client is not None
        mock_obj.login.assert_called_once()

        # Second call should NOT re-login
        client._ensure_connected()
        mock_obj.login.assert_called_once()  # still 1 call


def test_get_auto_reconnect_on_401():
    """Test get() retries once after 401 AuthenticationError."""
    config = RedfishConfig(
        host="https://192.168.100.23",
        username="admin",
        password="password123",
    )
    with patch("redfish_mcp_server.client.redfish_client.redfish_client") as mock_rf:
        mock_obj = MagicMock()
        mock_rf.return_value = mock_obj

        # First call returns 401, second returns 200
        mock_response_401 = MagicMock()
        mock_response_401.status = 401

        mock_response_200 = MagicMock()
        mock_response_200.status = 200
        mock_response_200.dict = {"Id": "1", "Name": "System"}

        mock_obj.get.side_effect = [mock_response_401, mock_response_200]

        client = RedfishClient(config)
        client._client = mock_obj
        result = client.get("/redfish/v1/Systems/1")

        assert result == {"Id": "1", "Name": "System"}
        assert mock_obj.get.call_count == 2
        # login should have been called (re-login after 401)
        mock_obj.login.assert_called()


def test_test_connection_calls_login_and_get():
    """Test test_connection() calls _login then get service root."""
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
        mock_response.dict = {"Name": "Redfish Service", "RedfishVersion": "1.8.0"}
        mock_obj.get.return_value = mock_response

        client = RedfishClient(config)
        result = client.test_connection()

        mock_obj.login.assert_called()
        mock_obj.get.assert_called_with("/redfish/v1/")
        assert result["Name"] == "Redfish Service"


if __name__ == "__main__":
    pytest.main([__file__])
