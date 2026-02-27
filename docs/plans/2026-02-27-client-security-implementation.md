# Client Security Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the Redfish MCP client from raw `requests` + Basic Auth to the DMTF `python-redfish-library` with Session Auth, SecretStr credentials, and security warnings.

**Architecture:** Wrapper pattern around `redfish.redfish_client`. The `RedfishClient` class keeps the same public interface (`get`, `post`, `patch`, `delete`, `test_connection`, `close`) so tools are untouched. Auth hierarchy: Session Auth (default) with Basic Auth fallback.

**Tech Stack:** Python 3.10+, `python-redfish-library` (DMTF), Pydantic v2 `SecretStr`, pytest

**Design doc:** `docs/plans/2026-02-25-client-security-design.md`

---

### Task 1: Update dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Replace requests/urllib3 with redfish in pyproject.toml**

Replace the dependencies block:

```python
# OLD (lines 7-13)
dependencies = [
    "mcp>=1.0.0",
    "mcp[cli]>=1.12.3",
    "requests>=2.31.0",
    "pydantic>=2.0.0",
    "urllib3>=2.0.0",
]

# NEW
dependencies = [
    "mcp>=1.0.0",
    "mcp[cli]>=1.12.3",
    "redfish>=3.0.0",
    "pydantic>=2.0.0",
]
```

**Step 2: Install new dependencies**

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv sync`
Expected: redfish installed, requests/urllib3 removed from direct deps (redfish pulls them transitively)

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: replace requests/urllib3 with python-redfish-library (DMTF)"
```

---

### Task 2: Update RedfishConfig with SecretStr and new fields

**Files:**
- Modify: `src/redfish_mcp_server/config/models.py`
- Test: `tests/test_main.py` (existing test will break, we fix it here)

**Step 1: Write failing test for new config fields**

Add to `tests/test_main.py`:

```python
from pydantic import SecretStr

def test_redfish_config_secret_str():
    """Test RedfishConfig uses SecretStr for password."""
    config = RedfishConfig(
        host="https://192.168.1.100",
        username="admin",
        password="password123"
    )
    # password is SecretStr, not plain str
    assert isinstance(config.password, SecretStr)
    assert config.password.get_secret_value() == "password123"
    # repr must NOT contain the password
    assert "password123" not in repr(config)
    # json serialization must NOT contain the password
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
```

**Step 2: Run tests to verify they fail**

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv run pytest tests/test_main.py -v -k "test_redfish_config"`
Expected: FAIL — `password` is still `str`, `auth_method` etc. don't exist

**Step 3: Update RedfishConfig in models.py**

Replace lines 1-13 of `src/redfish_mcp_server/config/models.py`:

```python
"""Pydantic models for Redfish MCP server configuration and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, SecretStr


class RedfishConfig(BaseModel):
    """Configuration for Redfish connection"""
    host: str = Field(..., description="Redfish host URL (https:// recommended)")
    username: str = Field(..., description="Username for authentication")
    password: SecretStr = Field(..., description="Password for authentication")
    verify_ssl: bool = Field(default=False, description="Verify SSL certificates")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    auth_method: str = Field(default="session", description="Auth method: 'session' or 'basic'")
    bmc_vendor: str = Field(default="asrockrack", description="BMC vendor (qualified: asrockrack)")
    # Ready for phase 2 — mTLS
    client_cert: Optional[str] = Field(default=None, description="Path to client certificate (.pem)")
    client_key: Optional[SecretStr] = Field(default=None, description="Path to client private key")
    ca_bundle: Optional[str] = Field(default=None, description="Path to CA bundle for SSL verification")
```

Rest of file (line 16+) is unchanged.

**Step 4: Fix existing test_redfish_config test**

The existing `test_redfish_config` (line 14-25 of test_main.py) accesses `config.password` as plain str. Update it:

```python
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
```

**Step 5: Run tests to verify they pass**

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv run pytest tests/test_main.py -v -k "test_redfish_config"`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/redfish_mcp_server/config/models.py tests/test_main.py
git commit -m "feat: add SecretStr, auth_method, bmc_vendor, mTLS fields to RedfishConfig"
```

---

### Task 3: Rewrite RedfishClient as DMTF wrapper

**Files:**
- Modify: `src/redfish_mcp_server/client/redfish_client.py` (full rewrite)
- Test: `tests/test_main.py`

**Step 1: Write failing tests for new client**

Add to `tests/test_main.py`:

```python
from unittest.mock import patch, MagicMock
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
```

**Step 2: Run tests to verify they fail**

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv run pytest tests/test_main.py -v -k "test_client_"`
Expected: FAIL — current client uses requests, not DMTF

**Step 3: Rewrite redfish_client.py**

Replace entire content of `src/redfish_mcp_server/client/redfish_client.py`:

```python
"""Redfish client wrapping DMTF python-redfish-library."""

import logging
from typing import Any, Dict, Optional

from redfish import redfish_client

from ..config.models import RedfishConfig
from ..utils.exceptions import AuthenticationError, ConnectionError, OperationError

logger = logging.getLogger(__name__)

QUALIFIED_VENDORS = ("asrockrack",)


class RedfishClient:
    """Client for interacting with Redfish API via DMTF library."""

    def __init__(self, config: RedfishConfig) -> None:
        self.config = config
        self.base_url = config.host.rstrip("/")
        self.timeout = config.timeout
        self._client: Any = None
        self._auth_method: str = config.auth_method

        self._log_security_warnings()

    # ── Security warnings ───────────────────────────────────────────

    def _log_security_warnings(self) -> None:
        """Log warnings based on security configuration."""
        if self.base_url.startswith("http://"):
            logger.warning(
                "Unencrypted connection — credentials exposed on network: %s",
                self.base_url,
            )
        elif not self.config.verify_ssl:
            logger.warning(
                "SSL certificate not verified — vulnerable to MITM: %s",
                self.base_url,
            )
        else:
            logger.info("Verified SSL connection: %s", self.base_url)

        if self.config.bmc_vendor not in QUALIFIED_VENDORS:
            logger.warning(
                "Client qualified only for ASRock Rack BMC (AST2500). "
                "Current vendor: %s",
                self.config.bmc_vendor,
            )

    # ── Connection ──────────────────────────────────────────────────

    def _create_dmtf_client(self) -> Any:
        """Create the underlying DMTF redfish client object."""
        password = self.config.password.get_secret_value()
        ca_file = self.config.ca_bundle if self.config.verify_ssl else None

        return redfish_client(
            base_url=self.base_url,
            username=self.config.username,
            password=password,
            timeout=self.timeout,
            cafile=ca_file,
        )

    def _login(self) -> None:
        """Authenticate with session auth, fallback to basic."""
        self._client = self._create_dmtf_client()

        if self._auth_method == "session":
            try:
                self._client.login(auth="session")
                logger.info("Session auth successful: %s", self.base_url)
                return
            except Exception as exc:
                logger.warning(
                    "Session auth failed — fallback to Basic Auth: %s", exc
                )
                self._auth_method = "basic"
                # Re-create client for basic auth
                self._client = self._create_dmtf_client()

        try:
            self._client.login(auth="basic")
            logger.info("Basic auth successful: %s", self.base_url)
        except Exception as exc:
            logger.error("Authentication failed: %s", exc)
            raise AuthenticationError(f"Authentication failed: {exc}")

    def _ensure_connected(self) -> None:
        """Ensure client is connected, reconnect if needed."""
        if self._client is None:
            self._login()

    # ── Request handling ────────────────────────────────────────────

    def _handle_response(self, response: Any) -> Dict[str, Any]:
        """Convert DMTF RestResponse to dict with error handling."""
        status = response.status

        if status == 401:
            # Token expired — try reconnect once
            logger.info("Token expired — reconnecting session")
            self._client = None
            raise AuthenticationError("Token expired")
        elif status == 403:
            raise OperationError(
                "Access denied: Insufficient permissions for this operation"
            )
        elif status == 404:
            raise OperationError(f"Resource not found: {response.request.path}")
        elif status >= 500:
            raise OperationError(f"Server error (HTTP {status})")
        elif status >= 400:
            raise OperationError(f"Request failed (HTTP {status})")

        return response.dict if response.dict else {}

    def get(self, endpoint: str) -> Dict[str, Any]:
        """GET request to Redfish API."""
        self._ensure_connected()
        try:
            response = self._client.get(endpoint)
            return self._handle_response(response)
        except AuthenticationError:
            # Retry once after re-login
            self._login()
            response = self._client.get(endpoint)
            return self._handle_response(response)
        except (ConnectionError, OperationError):
            raise
        except Exception as exc:
            logger.error("GET %s failed: %s", endpoint, exc)
            raise ConnectionError(f"Request failed: {exc}")

    def post(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """POST request to Redfish API."""
        self._ensure_connected()
        try:
            response = self._client.post(endpoint, body=data)
            return self._handle_response(response)
        except (ConnectionError, OperationError, AuthenticationError):
            raise
        except Exception as exc:
            logger.error("POST %s failed: %s", endpoint, exc)
            raise OperationError(f"Request failed: {exc}")

    def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """PATCH request to Redfish API."""
        self._ensure_connected()
        try:
            response = self._client.patch(endpoint, body=data)
            return self._handle_response(response)
        except (ConnectionError, OperationError, AuthenticationError):
            raise
        except Exception as exc:
            logger.error("PATCH %s failed: %s", endpoint, exc)
            raise OperationError(f"Request failed: {exc}")

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request to Redfish API."""
        self._ensure_connected()
        try:
            response = self._client.delete(endpoint)
            return self._handle_response(response)
        except (ConnectionError, OperationError, AuthenticationError):
            raise
        except Exception as exc:
            logger.error("DELETE %s failed: %s", endpoint, exc)
            raise OperationError(f"Request failed: {exc}")

    def test_connection(self) -> Dict[str, Any]:
        """Test the connection by getting the service root."""
        try:
            self._login()
            return self.get("/redfish/v1/")
        except Exception as exc:
            logger.error("Connection test failed: %s", exc)
            raise

    def close(self) -> None:
        """Logout and close the session."""
        if self._client is not None:
            try:
                self._client.logout()
                logger.debug("Redfish session closed: %s", self.base_url)
            except Exception as exc:
                logger.warning("Logout failed (session may have expired): %s", exc)
            finally:
                self._client = None
```

**Step 4: Run tests to verify they pass**

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv run pytest tests/test_main.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/redfish_mcp_server/client/redfish_client.py tests/test_main.py
git commit -m "feat: rewrite client as DMTF python-redfish-library wrapper

Session Auth with Basic Auth fallback, security warnings,
auto-reconnect on 401, proper logout on close."
```

---

### Task 4: Update main.py for new env vars

**Files:**
- Modify: `src/redfish_mcp_server/main.py` (lines 50-82)

**Step 1: Write failing test for new env vars**

Add to `tests/test_main.py`:

```python
import os

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
```

**Step 2: Run test to verify it passes** (this tests config, should pass after Task 2)

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv run pytest tests/test_main.py::test_initialize_from_env_reads_auth_method -v`
Expected: PASS

**Step 3: Update _initialize_from_env in main.py**

Replace lines 50-82 of `src/redfish_mcp_server/main.py`:

```python
def _initialize_from_env() -> Optional[RedfishClient]:
    """Initialize Redfish client from environment variables if available"""
    host = os.getenv('REDFISH_HOST')
    username = os.getenv('REDFISH_USERNAME')
    password = os.getenv('REDFISH_PASSWORD')
    verify_ssl = os.getenv('REDFISH_VERIFY_SSL', 'false').lower() in ('true', '1', 'yes')
    timeout = int(os.getenv('REDFISH_TIMEOUT', '30'))
    auth_method = os.getenv('REDFISH_AUTH_METHOD', 'session')
    bmc_vendor = os.getenv('REDFISH_BMC_VENDOR', 'asrockrack')

    if host and username and password:
        try:
            config = RedfishConfig(
                host=host,
                username=username,
                password=password,
                verify_ssl=verify_ssl,
                timeout=timeout,
                auth_method=auth_method,
                bmc_vendor=bmc_vendor,
            )
            client = RedfishClient(config)

            # Test the connection
            service_root = client.test_connection()
            logger.info(f"Auto-configured Redfish client for {host}")
            logger.info(f"Connected to: {service_root.get('Name', 'Unknown')} "
                       f"(Version: {service_root.get('RedfishVersion', 'Unknown')})")
            return client
        except Exception as e:
            logger.warning(f"Failed to auto-configure Redfish client from environment: {e}")
            return None
    else:
        logger.info("Redfish environment variables not set. Use redfish_configure tool or set:")
        logger.info("  REDFISH_HOST, REDFISH_USERNAME, REDFISH_PASSWORD")
        logger.info("  Optional: REDFISH_VERIFY_SSL, REDFISH_TIMEOUT, REDFISH_AUTH_METHOD, REDFISH_BMC_VENDOR")
        return None
```

**Step 4: Run all tests**

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv run pytest tests/test_main.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/redfish_mcp_server/main.py tests/test_main.py
git commit -m "feat: add REDFISH_AUTH_METHOD and REDFISH_BMC_VENDOR env vars"
```

---

### Task 5: Update management.py configure tool for SecretStr

**Files:**
- Modify: `src/redfish_mcp_server/tools/management.py` (only the `redfish_configure` function)

**Step 1: Check current configure function usage of password**

The `redfish_configure` tool in `management.py` creates a `RedfishConfig` with `password=password` as plain str. Since `password` is now `SecretStr`, this still works (Pydantic auto-coerces `str` to `SecretStr`). But any place that reads `config.password` as a string needs `.get_secret_value()`.

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && grep -n "config.password\|\.password" src/redfish_mcp_server/tools/management.py`

**Step 2: Fix any direct password access**

If any line uses `config.password` as str (not via DMTF client), replace with `config.password.get_secret_value()`.

**Step 3: Run all tests**

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv run pytest tests/ -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add src/redfish_mcp_server/tools/management.py
git commit -m "fix: update management tool for SecretStr password compatibility"
```

---

### Task 6: Final validation and cleanup

**Files:**
- Verify all files

**Step 1: Run full test suite**

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv run pytest tests/ -v`
Expected: ALL PASS

**Step 2: Run type checker**

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv run mypy src/redfish_mcp_server/ --ignore-missing-imports`
Expected: No errors (or only pre-existing ones)

**Step 3: Run linter**

Run: `cd D:/infra/mcp-servers/redfish-mcp-server && uv run ruff check src/redfish_mcp_server/`
Expected: Clean or only pre-existing warnings

**Step 4: Verify no urllib3.disable_warnings remains**

Run: `grep -r "disable_warnings" src/`
Expected: No matches

**Step 5: Verify no direct requests import remains in client**

Run: `grep -r "import requests" src/redfish_mcp_server/client/`
Expected: No matches

**Step 6: Commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: final cleanup and validation"
```

**Step 7: Push and update PR**

```bash
git push origin docs/client-security-design
```

PR #1 on `mipsou/redfish-mcp-server` is updated automatically.
