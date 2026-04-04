"""Organization management — list, get, update organizations.

Organizations are the top-level container in IcePanel. They contain
landscapes, teams, users, and technologies.
"""

from cli_anything.icepanel.utils.icepanel_backend import (
    api_get,
    api_post,
    api_patch,
    api_delete,
    _get_default_org_id,
)


def _require_org_id(org_id: str | None) -> str:
    """Resolve organization ID from argument or default config."""
    resolved = org_id or _get_default_org_id()
    if not resolved:
        raise RuntimeError(
            "Organization ID required. Pass --org-id or set default with: "
            "auth set-defaults --org-id <ID>"
        )
    return resolved


def list_organizations() -> dict:
    """List all organizations accessible with the current API key."""
    data = api_get("/organizations")
    orgs = data.get("organizations", [])
    return {
        "count": len(orgs),
        "organizations": [_format_org(o) for o in orgs],
    }


def get_organization(org_id: str | None = None) -> dict:
    """Get details for a specific organization."""
    oid = _require_org_id(org_id)
    data = api_get(f"/organizations/{oid}")
    return _format_org(data.get("organization", data))


def update_organization(org_id: str | None = None, **kwargs) -> dict:
    """Update organization properties.

    Supported fields: name, language, shareLinksEnabled, aiFeaturesEnabled,
    lineShapeDefault.
    """
    oid = _require_org_id(org_id)
    body = {k: v for k, v in kwargs.items() if v is not None}
    if not body:
        raise ValueError("No fields provided for update.")
    data = api_patch(f"/organizations/{oid}", body)
    return _format_org(data.get("organization", data))


def list_landscapes(org_id: str | None = None) -> dict:
    """List all landscapes in an organization."""
    oid = _require_org_id(org_id)
    data = api_get(f"/organizations/{oid}/landscapes")
    landscapes = data.get("landscapes", [])
    return {
        "count": len(landscapes),
        "landscapes": [_format_landscape_summary(ls) for ls in landscapes],
    }


def create_landscape(name: str, org_id: str | None = None) -> dict:
    """Create a new landscape in an organization.

    Args:
        name: Landscape name.
        org_id: Organization ID (uses default if not specified).

    Returns:
        Created landscape and version dict.
    """
    oid = _require_org_id(org_id)
    data = api_post(f"/organizations/{oid}/landscapes", {"name": name})
    return {
        "landscape": _format_landscape_summary(data.get("landscape", {})),
        "version": data.get("version", {}),
    }


def list_users(org_id: str | None = None) -> dict:
    """List all users in an organization."""
    oid = _require_org_id(org_id)
    data = api_get(f"/organizations/{oid}/users")
    raw_users = data.get("organizationUsers", {})
    users = [_format_user(uid, udata) for uid, udata in raw_users.items()]
    return {"count": len(users), "users": users}


def list_user_invites(org_id: str | None = None) -> dict:
    """List pending user invites."""
    oid = _require_org_id(org_id)
    data = api_get(f"/organizations/{oid}/users/invites")
    return data


def create_user_invite(
    email: str,
    permission: str = "editor",
    org_id: str | None = None,
    **kwargs,
) -> dict:
    """Invite a user to the organization.

    Args:
        email: User's email address.
        permission: Permission level (admin, editor, viewer).
    """
    oid = _require_org_id(org_id)
    body = {"email": email, "permission": permission}
    body.update({k: v for k, v in kwargs.items() if v is not None})
    data = api_post(f"/organizations/{oid}/users/invites", body)
    return data.get("organizationUserInvite", data)


def list_technologies(org_id: str | None = None) -> dict:
    """List the technology catalog for an organization."""
    oid = _require_org_id(org_id)
    data = api_get(f"/organizations/{oid}/technologies")
    techs = data.get("catalogTechnologies", [])
    return {
        "count": len(techs),
        "technologies": [_format_tech(t) for t in techs],
    }


def _format_tech(data: dict) -> dict:
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "name_short": data.get("nameShort", ""),
        "type": data.get("type"),
        "provider": data.get("provider"),
        "status": data.get("status", ""),
        "color": data.get("color", ""),
    }


def _format_user(uid: str, data: dict) -> dict:
    return {
        "user_id": uid,
        "email": data.get("email", ""),
        "name": data.get("name", ""),
        "permission": data.get("permission", ""),
        "last_active_at": data.get("lastActiveAt", ""),
    }


def _format_org(data: dict) -> dict:
    """Format organization for output."""
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "plan": data.get("plan", ""),
        "status": data.get("status", ""),
        "seats": data.get("seats", 0),
        "user_count": len(data.get("userIds", [])),
        "created_at": data.get("createdAt", ""),
    }


def _format_landscape_summary(data: dict) -> dict:
    """Format landscape list item."""
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "created_at": data.get("createdAt", ""),
        "updated_at": data.get("updatedAt", ""),
    }
