"""Authentication — API key setup and validation.

IcePanel uses API keys generated from the organization management screen.
The key format is: "<keyId>:<keySecret>"
Header format: "Authorization: ApiKey <keyId>:<keySecret>"

Generate keys at: https://app.icepanel.io → Organization Settings → API Keys
"""

from cli_anything.icepanel.utils.icepanel_backend import (
    load_config,
    save_config,
    api_get,
    CONFIG_DIR,
)


def setup_api_key(
    api_key: str,
    organization_id: str | None = None,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Save API key and optional defaults.

    Args:
        api_key: IcePanel API key in format "keyId:keySecret".
        organization_id: Default organization ID for commands.
        landscape_id: Default landscape ID for commands.
        version_id: Default version ID (default: "latest").

    Returns:
        Confirmation dict with saved config path.
    """
    config = load_config()
    config["api_key"] = api_key
    if organization_id:
        config["organization_id"] = organization_id
    if landscape_id:
        config["landscape_id"] = landscape_id
    if version_id:
        config["version_id"] = version_id
    save_config(config)

    return {
        "status": "configured",
        "config_path": str(CONFIG_DIR / "config.json"),
        "organization_id": config.get("organization_id"),
        "landscape_id": config.get("landscape_id"),
    }


def set_defaults(
    organization_id: str | None = None,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Update default organization, landscape, or version without changing API key.

    Returns:
        Updated config dict.
    """
    config = load_config()
    if not config.get("api_key"):
        raise RuntimeError("Not authenticated. Run 'auth setup --api-key <KEY>' first.")
    if organization_id:
        config["organization_id"] = organization_id
    if landscape_id:
        config["landscape_id"] = landscape_id
    if version_id:
        config["version_id"] = version_id
    save_config(config)

    return {
        "status": "updated",
        "organization_id": config.get("organization_id"),
        "landscape_id": config.get("landscape_id"),
        "version_id": config.get("version_id", "latest"),
    }


def get_auth_status() -> dict:
    """Check current authentication status.

    Validates the API key by listing organizations.

    Returns:
        Dict with auth status, configured defaults, and validation result.
    """
    config = load_config()

    result = {
        "configured": bool(config.get("api_key")),
        "authenticated": False,
        "organization_id": config.get("organization_id"),
        "landscape_id": config.get("landscape_id"),
        "version_id": config.get("version_id", "latest"),
        "config_path": str(CONFIG_DIR / "config.json"),
    }

    if not config.get("api_key"):
        return result

    # Validate by listing organizations
    try:
        data = api_get("/organizations")
        orgs = data.get("organizations", [])
        result["authenticated"] = True
        result["organizations_count"] = len(orgs)
        if orgs:
            result["organizations"] = [
                {"id": o["id"], "name": o["name"], "plan": o.get("plan", "unknown")}
                for o in orgs
            ]
    except Exception as e:
        result["authenticated"] = False
        result["error"] = str(e)

    return result


def logout() -> dict:
    """Remove saved API key and config.

    Returns:
        Confirmation dict.
    """
    config_file = CONFIG_DIR / "config.json"
    if config_file.exists():
        config_file.unlink()
    return {"status": "logged_out", "message": "Local config removed."}
