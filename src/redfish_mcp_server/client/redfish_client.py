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

    # -- Security warnings ---------------------------------------------------

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

    # -- Connection ----------------------------------------------------------

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

    # -- Request handling ----------------------------------------------------

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
