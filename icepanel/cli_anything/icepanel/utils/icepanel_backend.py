"""IcePanel API backend — wraps IcePanel REST API v1.

This module handles all HTTP communication with the IcePanel API.
It is the only module that makes network requests.

Authentication:
    IcePanel uses API keys generated from the organization management screen.
    Format: "ApiKey <keyId>:<keySecret>"
    Header: Authorization: ApiKey SH5XAi...:17a9c6...

Base URL: https://api.icepanel.io/v1
"""

import json
import os
import fcntl
from pathlib import Path
from typing import Any, Optional

import requests


# IcePanel API base URL
API_BASE = "https://api.icepanel.io/v1"

# Default config directory
CONFIG_DIR = Path.home() / ".cli-anything-icepanel"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _restrict_path(path: Path, mode: int):
    """Set file/directory permissions (owner-only)."""
    try:
        path.chmod(mode)
    except OSError:
        pass


def get_config_dir() -> Path:
    """Get or create config directory with owner-only permissions (0o700)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _restrict_path(CONFIG_DIR, 0o700)
    return CONFIG_DIR


def load_config() -> dict:
    """Load config (api_key, organization_id, default landscape, etc.)."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config: dict):
    """Save config with owner-only permissions (0o600).

    Uses file locking to prevent concurrent write corruption.
    """
    get_config_dir()
    tmp = CONFIG_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(config, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.rename(CONFIG_FILE)
    _restrict_path(CONFIG_FILE, 0o600)


def _get_api_key() -> str:
    """Load API key from config or ICEPANEL_API_KEY env var.

    Priority: env var > config file.
    """
    key = os.environ.get("ICEPANEL_API_KEY")
    if key:
        return key
    config = load_config()
    key = config.get("api_key")
    if not key:
        raise RuntimeError(
            "Not authenticated. Run 'auth setup --api-key <KEY>' first.\n"
            "Generate an API key at: https://app.icepanel.io → Organization Settings → API Keys"
        )
    return key


def _get_default_org_id() -> Optional[str]:
    """Get default organization ID from config or env."""
    org_id = os.environ.get("ICEPANEL_ORG_ID")
    if org_id:
        return org_id
    return load_config().get("organization_id")


def _get_default_landscape_id() -> Optional[str]:
    """Get default landscape ID from config or env."""
    lid = os.environ.get("ICEPANEL_LANDSCAPE_ID")
    if lid:
        return lid
    return load_config().get("landscape_id")


def _get_default_version_id() -> str:
    """Get default version ID from config or env. Defaults to 'latest'."""
    vid = os.environ.get("ICEPANEL_VERSION_ID")
    if vid:
        return vid
    return load_config().get("version_id", "latest")


def api_request(
    method: str,
    endpoint: str,
    params: Optional[dict] = None,
    json_data: Optional[dict] = None,
    stream: bool = False,
) -> Any:
    """Make an authenticated request to the IcePanel API.

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD).
        endpoint: API endpoint path (e.g., '/landscapes/{id}').
        params: Query parameters.
        json_data: JSON request body.
        stream: Whether to stream the response.

    Returns:
        Parsed JSON response, or raw Response if streaming.

    Raises:
        requests.HTTPError: On non-2xx responses.
        RuntimeError: If not authenticated.
    """
    api_key = _get_api_key()
    url = f"{API_BASE}{endpoint}"
    headers = {
        "Authorization": f"ApiKey {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    resp = requests.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json_data,
        stream=stream,
        timeout=60,
    )

    if stream and resp.status_code == 200:
        return resp

    # Raise with body context for better error messages
    if not resp.ok:
        try:
            err_body = resp.json()
            msg = err_body.get("message", resp.text)
        except Exception:
            msg = resp.text
        raise requests.HTTPError(
            f"IcePanel API {method} {endpoint} → {resp.status_code}: {msg}",
            response=resp,
        )

    if resp.status_code == 204 or method.upper() == "HEAD":
        return {"status": "success", "status_code": resp.status_code}

    # Some endpoints return plain text (e.g., Mermaid/text/code flow exports)
    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return resp.json()
    elif "text/" in content_type:
        return {"content": resp.text, "content_type": content_type}
    else:
        # Try JSON first, fall back to text
        try:
            return resp.json()
        except Exception:
            return {"content": resp.text, "content_type": content_type}


def api_get(endpoint: str, params: Optional[dict] = None) -> Any:
    """Shorthand for GET request."""
    return api_request("GET", endpoint, params=params)


def api_post(endpoint: str, data: Optional[dict] = None) -> Any:
    """Shorthand for POST request."""
    return api_request("POST", endpoint, json_data=data)


def api_put(endpoint: str, data: Optional[dict] = None) -> Any:
    """Shorthand for PUT request."""
    return api_request("PUT", endpoint, json_data=data)


def api_patch(endpoint: str, data: Optional[dict] = None) -> Any:
    """Shorthand for PATCH request."""
    return api_request("PATCH", endpoint, json_data=data)


def api_delete(endpoint: str) -> Any:
    """Shorthand for DELETE request."""
    return api_request("DELETE", endpoint)


def api_head(endpoint: str) -> Any:
    """Shorthand for HEAD request (existence check)."""
    return api_request("HEAD", endpoint)
