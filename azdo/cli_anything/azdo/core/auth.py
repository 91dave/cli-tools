"""Authentication — Azure DevOps connection setup and validation.

Uses `az account get-access-token` for bearer token auth.
PAT fallback via AZDO_PAT environment variable.

Prerequisites:
    1. Azure CLI installed: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
    2. Logged in: az login --tenant adammatthewdigital.onmicrosoft.com
"""

from cli_anything.azdo.utils.azdo_backend import (
    load_config,
    save_config,
    api_get,
    get_auth_header,
    CONFIG_DIR,
)


def set_defaults(
    organization: str | None = None,
    project: str | None = None,
    tenant: str | None = None,
) -> dict:
    """Save org/project/tenant defaults.

    Args:
        organization: Azure DevOps organization name.
        project: Azure DevOps project name.
        tenant: Azure AD tenant for token acquisition.

    Returns:
        Confirmation dict with updated values.
    """
    config = load_config()
    if organization:
        config["organization"] = organization
    if project:
        config["project"] = project
    if tenant:
        config["tenant"] = tenant
    save_config(config)

    return {
        "status": "updated",
        "organization": config.get("organization"),
        "project": config.get("project"),
        "tenant": config.get("tenant"),
        "config_path": str(CONFIG_DIR / "config.json"),
    }


def get_auth_status() -> dict:
    """Check current authentication status.

    Validates by calling GET /projects/{project} on Azure DevOps.

    Returns:
        Dict with auth status, configured defaults, and validation result.
    """
    config = load_config()

    has_org = bool(config.get("organization"))
    has_project = bool(config.get("project"))
    has_tenant = bool(config.get("tenant"))
    configured = has_org and has_project and has_tenant

    result = {
        "configured": configured,
        "authenticated": False,
        "organization": config.get("organization"),
        "project": config.get("project"),
        "tenant": config.get("tenant"),
        "config_path": str(CONFIG_DIR / "config.json"),
    }

    if not configured:
        return result

    # Validate by fetching project info
    try:
        get_auth_header()  # will raise if token acquisition fails
        data = api_get(
            f"/projects/{config['project']}",
            use_project=False,
        )
        result["authenticated"] = True
        result["project_name"] = data.get("name")
        result["project_id"] = data.get("id")
        result["project_state"] = data.get("state")
    except Exception as e:
        result["authenticated"] = False
        result["error"] = str(e)

    return result
