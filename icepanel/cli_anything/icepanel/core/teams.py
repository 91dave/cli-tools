"""Team management — CRUD for teams within an organization."""

from cli_anything.icepanel.utils.icepanel_backend import (
    api_get,
    api_post,
    api_patch,
    api_delete,
    _get_default_org_id,
)


def _require_org_id(org_id: str | None) -> str:
    resolved = org_id or _get_default_org_id()
    if not resolved:
        raise RuntimeError("Organization ID required.")
    return resolved


def list_teams(org_id: str | None = None) -> dict:
    """List all teams."""
    oid = _require_org_id(org_id)
    data = api_get(f"/organizations/{oid}/teams")
    teams = data.get("teams", [])
    return {"count": len(teams), "teams": [_fmt(t) for t in teams]}


def create_team(name: str, color: str = "blue", org_id: str | None = None, **kwargs) -> dict:
    """Create a team."""
    oid = _require_org_id(org_id)
    body = {"name": name, "color": color}
    body.update({k: v for k, v in kwargs.items() if v is not None})
    data = api_post(f"/organizations/{oid}/teams", body)
    return data.get("team", data)


def get_team(team_id: str, org_id: str | None = None) -> dict:
    """Get a team."""
    oid = _require_org_id(org_id)
    data = api_get(f"/organizations/{oid}/teams/{team_id}")
    return _fmt(data.get("team", data))


def update_team(team_id: str, org_id: str | None = None, **kwargs) -> dict:
    """Update a team."""
    oid = _require_org_id(org_id)
    body = {k: v for k, v in kwargs.items() if v is not None}
    if not body:
        raise ValueError("No fields provided.")
    data = api_patch(f"/organizations/{oid}/teams/{team_id}", body)
    return data.get("team", data)


def delete_team(team_id: str, org_id: str | None = None) -> dict:
    """Delete a team."""
    oid = _require_org_id(org_id)
    return api_delete(f"/organizations/{oid}/teams/{team_id}")


def list_team_landscapes(team_id: str, org_id: str | None = None) -> dict:
    """List landscapes a team has access to."""
    oid = _require_org_id(org_id)
    return api_get(f"/organizations/{oid}/teams/{team_id}/landscapes")


def list_team_model_objects(team_id: str, org_id: str | None = None) -> dict:
    """List model objects owned by a team."""
    oid = _require_org_id(org_id)
    return api_get(f"/organizations/{oid}/teams/{team_id}/model/objects")


def _fmt(data: dict) -> dict:
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "color": data.get("color", ""),
        "user_ids": data.get("userIds", []),
        "model_object_handle_ids": data.get("modelObjectHandleIds", []),
        "organization_id": data.get("organizationId", ""),
    }
