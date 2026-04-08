"""Azure DevOps API backend — wraps Azure DevOps REST API v7.1.

This module handles all HTTP communication with Azure DevOps.
It is the only module that makes network requests.

Authentication:
    Primary: Bearer token via `az account get-access-token`
    Fallback: PAT via AZDO_PAT env var (HTTP Basic auth)

Base URL: https://dev.azure.com/{org}/{project}/_apis
"""

import base64
import json
import os
import shutil
import sys
import subprocess
from pathlib import Path
from typing import Any, Optional

import requests


# Azure DevOps API version
API_VERSION = "7.1"

# Azure DevOps resource ID for token acquisition
AZDO_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"

# Default config directory
CONFIG_DIR = Path.home() / ".cli-anything-azdo"
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
    """Load config from disk."""
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
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(config, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.rename(CONFIG_FILE)
    _restrict_path(CONFIG_FILE, 0o600)


# ── Config resolution (env var → config file → raise) ────────────

def get_org() -> str:
    """Get organization name. Priority: env var > config."""
    val = os.environ.get("AZDO_ORG")
    if val:
        return val
    val = load_config().get("organization")
    if val:
        return val
    raise RuntimeError(
        "Organization not configured. Run: cli-anything-azdo auth set-defaults --org <ORG>"
    )


def get_project() -> str:
    """Get project name. Priority: env var > config."""
    val = os.environ.get("AZDO_PROJECT")
    if val:
        return val
    val = load_config().get("project")
    if val:
        return val
    raise RuntimeError(
        "Project not configured. Run: cli-anything-azdo auth set-defaults --project <PROJECT>"
    )


def get_tenant() -> str:
    """Get tenant name. Priority: env var > config."""
    val = os.environ.get("AZDO_TENANT")
    if val:
        return val
    val = load_config().get("tenant")
    if val:
        return val
    raise RuntimeError(
        "Tenant not configured. Run: cli-anything-azdo auth set-defaults --tenant <TENANT>"
    )


# ── Token acquisition ────────────────────────────────────────────

def get_token() -> str:
    """Acquire a bearer token via `az account get-access-token`.

    Returns:
        Token string.

    Raises:
        RuntimeError: If az CLI fails (e.g. not logged in).
    """
    tenant = get_tenant()
    az_path = shutil.which("az")
    if az_path is None:
        raise RuntimeError(
            "Azure CLI ('az') not found on PATH. "
            "Install it from https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
        )
    result = subprocess.run(
        [
            az_path, "account", "get-access-token",
            "--resource", AZDO_RESOURCE_ID,
            "--tenant", tenant,
            "--query", "accessToken",
            "-o", "tsv",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to acquire Azure DevOps token. "
            f"Please run 'az login --tenant {tenant}' first.\n"
            f"Error: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def get_auth_header() -> dict:
    """Get the Authorization header.

    Uses PAT (AZDO_PAT env var) if set, otherwise az CLI token.

    Returns:
        Dict with Authorization header.
    """
    pat = os.environ.get("AZDO_PAT")
    if pat:
        encoded = base64.b64encode(f":{pat}".encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    token = get_token()
    return {"Authorization": f"Bearer {token}"}


# ── API request helpers ──────────────────────────────────────────

def api_request(
    method: str,
    endpoint: str,
    params: Optional[dict] = None,
    json_data: Optional[dict | list] = None,
    project: Optional[str] = None,
    use_project: bool = True,
    content_type: str = "application/json",
    api_version: Optional[str] = None,
) -> Any:
    """Make an authenticated request to the Azure DevOps API.

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE).
        endpoint: API endpoint path (e.g., '/wit/workitems/123').
        params: Additional query parameters.
        json_data: JSON request body.
        project: Override project (None = use default, False-ish = org-level).
        use_project: If False, omit project from URL (org-level endpoint).
        content_type: Content-Type header value.

    Returns:
        Parsed JSON response.

    Raises:
        RuntimeError: On non-2xx responses or auth failure.
    """
    auth_header = get_auth_header()
    org = get_org()

    if use_project:
        proj = project or get_project()
        url = f"https://dev.azure.com/{org}/{proj}/_apis{endpoint}"
    else:
        url = f"https://dev.azure.com/{org}/_apis{endpoint}"

    headers = {
        **auth_header,
        "Accept": "application/json",
        "Content-Type": content_type,
    }

    all_params = {"api-version": api_version or API_VERSION}
    if params:
        all_params.update(params)

    resp = requests.request(
        method,
        url,
        headers=headers,
        params=all_params,
        json=json_data,
        timeout=60,
    )

    if not resp.ok:
        # Try to extract error message from response
        try:
            body = resp.content.decode("utf-8-sig")
            err = json.loads(body)
            msg = err.get("message", body)
        except Exception:
            msg = resp.content.decode("utf-8-sig", errors="replace")
        raise RuntimeError(
            f"Azure DevOps API {method} {endpoint} → {resp.status_code}: {msg}"
        )

    if resp.status_code == 204:
        return {"status": "success", "status_code": 204}

    # Decode with utf-8-sig to strip BOM
    body = resp.content.decode("utf-8-sig")
    return json.loads(body)


def api_get(endpoint: str, params: Optional[dict] = None, **kwargs) -> Any:
    """Shorthand for GET request."""
    return api_request("GET", endpoint, params=params, **kwargs)


def api_post(endpoint: str, data: Optional[dict | list] = None, **kwargs) -> Any:
    """Shorthand for POST request."""
    return api_request("POST", endpoint, json_data=data, **kwargs)


def api_patch(endpoint: str, data: Optional[list] = None, **kwargs) -> Any:
    """Shorthand for PATCH request (JSON Patch format for work items)."""
    return api_request(
        "PATCH", endpoint, json_data=data,
        content_type="application/json-patch+json", **kwargs
    )


def api_delete(endpoint: str, **kwargs) -> Any:
    """Shorthand for DELETE request."""
    return api_request("DELETE", endpoint, **kwargs)
