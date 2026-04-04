"""Version management — list, create, get, update, delete versions + reverts.

Versions represent snapshots of a landscape's architecture. The special
version ID "latest" always refers to the current working state.
"""

from cli_anything.icepanel.utils.icepanel_backend import (
    api_get,
    api_post,
    api_patch,
    api_delete,
    _get_default_landscape_id,
    _get_default_version_id,
)


def _require_lid(lid: str | None) -> str:
    resolved = lid or _get_default_landscape_id()
    if not resolved:
        raise RuntimeError("Landscape ID required.")
    return resolved


def list_versions(landscape_id: str | None = None) -> dict:
    """List all versions for a landscape."""
    lid = _require_lid(landscape_id)
    data = api_get(f"/landscapes/{lid}/versions")
    versions = data.get("versions", [])
    return {"count": len(versions), "versions": [_fmt(v) for v in versions]}


def create_version(name: str, notes: str = "", landscape_id: str | None = None) -> dict:
    """Create a new version (tag/snapshot)."""
    lid = _require_lid(landscape_id)
    data = api_post(f"/landscapes/{lid}/versions", {"name": name, "notes": notes})
    return _fmt(data.get("version", data))


def get_version(version_id: str | None = None, landscape_id: str | None = None) -> dict:
    """Get details of a specific version."""
    lid = _require_lid(landscape_id)
    vid = version_id or _get_default_version_id()
    data = api_get(f"/landscapes/{lid}/versions/{vid}")
    return _fmt(data.get("version", data))


def update_version(
    version_id: str, landscape_id: str | None = None,
    name: str | None = None, notes: str | None = None,
) -> dict:
    """Update a version's name or notes."""
    lid = _require_lid(landscape_id)
    body = {}
    if name is not None:
        body["name"] = name
    if notes is not None:
        body["notes"] = notes
    if not body:
        raise ValueError("No fields provided for update.")
    data = api_patch(f"/landscapes/{lid}/versions/{version_id}", body)
    return _fmt(data.get("version", data))


def delete_version(version_id: str, landscape_id: str | None = None) -> dict:
    """Delete a version."""
    lid = _require_lid(landscape_id)
    api_delete(f"/landscapes/{lid}/versions/{version_id}")
    return {"status": "deleted", "version_id": version_id}


# ── Reverts ──────────────────────────────────────────────────────

def list_reverts(landscape_id: str | None = None) -> dict:
    """List version reverts for a landscape."""
    lid = _require_lid(landscape_id)
    return api_get(f"/landscapes/{lid}/version/reverts")


def create_revert(version_id: str, notes: str = "", landscape_id: str | None = None) -> dict:
    """Create a version revert — roll back to a previous version."""
    lid = _require_lid(landscape_id)
    data = api_post(f"/landscapes/{lid}/version/reverts", {"versionId": version_id, "notes": notes})
    return data.get("versionRevert", data)


def get_revert(revert_id: str, landscape_id: str | None = None) -> dict:
    """Get revert details."""
    lid = _require_lid(landscape_id)
    data = api_get(f"/landscapes/{lid}/version/reverts/{revert_id}")
    return data.get("versionRevert", data)


def _fmt(data: dict) -> dict:
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "notes": data.get("notes", ""),
        "landscape_id": data.get("landscapeId", ""),
        "tags": data.get("tags", []),
        "created_at": data.get("createdAt", ""),
        "updated_at": data.get("updatedAt", ""),
    }
