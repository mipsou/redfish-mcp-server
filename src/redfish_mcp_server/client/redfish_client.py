"""Redfish client for API interactions."""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
import urllib3

from ..config.models import RedfishConfig
from ..utils.exceptions import ConnectionError, AuthenticationError, OperationError

# Disable SSL warnings for self-signed certificates (common in BMCs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class RedfishClient:
    """Client for interacting with Redfish API"""

    def __init__(self, config: RedfishConfig):
        self.config = config
        self.session = requests.Session()
        self.session.auth = (config.username, config.password)
        self.session.verify = config.verify_ssl
        self.timeout = config.timeout
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.base_url = config.host.rstrip('/')

        logger.info(f"Initialized Redfish client for {self.base_url}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Redfish API"""
        url = urljoin(self.base_url, endpoint)
        try:
            # Add timeout to the request kwargs
            kwargs.setdefault('timeout', self.timeout)
            logger.debug(f"Making {method} request to {url}")

            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            result = response.json() if response.content else {}
            logger.debug(f"Request successful: {method} {endpoint}")
            return result

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection failed to {url}: {e}")
            raise ConnectionError(f"Connection failed: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout for {url}: {e}")
            raise ConnectionError(f"Request timeout: {e}")
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            logger.error(f"HTTP error {status_code} for {url}: {e}")
            
            # Handle specific HTTP status codes with user-friendly messages
            if status_code == 401:
                raise AuthenticationError("Authentication failed: Invalid username or password")
            elif status_code == 403:
                raise OperationError("Access denied: Insufficient permissions for this operation")
            elif status_code == 404:
                # Check if this is a system-related endpoint
                if "/Systems/" in endpoint:
                    system_id = endpoint.split("/Systems/")[-1].split("/")[0]
                    raise OperationError(f"System '{system_id}' not found")
                elif "/Chassis/" in endpoint:
                    chassis_id = endpoint.split("/Chassis/")[-1].split("/")[0]
                    raise OperationError(f"Chassis '{chassis_id}' not found")
                elif "/Managers/" in endpoint:
                    manager_id = endpoint.split("/Managers/")[-1].split("/")[0]
                    raise OperationError(f"Manager '{manager_id}' not found")
                else:
                    raise OperationError(f"Resource not found: {endpoint}")
            elif status_code == 500:
                raise OperationError("Server error: Redfish service encountered an internal error")
            elif status_code == 503:
                raise OperationError("Service unavailable: Redfish service is temporarily unavailable")
            else:
                raise OperationError(f"HTTP error {status_code}: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise OperationError(f"Request failed: {e}")

    def get(self, endpoint: str) -> Dict[str, Any]:
        """GET request to Redfish API"""
        return self._make_request('GET', endpoint)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST request to Redfish API"""
        return self._make_request('POST', endpoint, json=data)

    def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """PATCH request to Redfish API"""
        return self._make_request('PATCH', endpoint, json=data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request to Redfish API"""
        return self._make_request('DELETE', endpoint)

    def test_connection(self) -> Dict[str, Any]:
        """Test the connection by getting the service root"""
        try:
            return self.get("/redfish/v1/")
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise

    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()
            logger.debug("Redfish client session closed")
