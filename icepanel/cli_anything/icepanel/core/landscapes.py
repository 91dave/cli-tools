"""Landscape management — get, update, delete, copy, duplicate, export, import, search.

Landscapes are the primary workspace in IcePanel. They contain versions,
model objects, connections, diagrams, flows, tags, and domains.

Most operations below this level require a landscapeId and versionId.
"""

from typing import Any

from cli_anything.icepanel.utils.icepanel_backend import (
    api_get,
    api_post,
    api_patch,
    api_delete,
    _get_default_landscape_id,
    _get_default_version_id,
)


def _require_landscape_id(lid: str | None) -> str:
    """Resolve landscape ID from argument or default config."""
    resolved = lid or _get_default_landscape_id()
    if not resolved:
        raise RuntimeError(
            "Landscape ID required. Pass --landscape-id or set default with: "
            "auth set-defaults --landscape-id <ID>"
        )
    return resolved


def get_landscape(landscape_id: str | None = None) -> dict:
    """Get landscape details."""
    lid = _require_landscape_id(landscape_id)
    return api_get(f"/landscapes/{lid}")


def update_landscape(landscape_id: str | None = None, **kwargs) -> dict:
    """Update landscape properties (name, description, etc.)."""
    lid = _require_landscape_id(landscape_id)
    body = {k: v for k, v in kwargs.items() if v is not None}
    if not body:
        raise ValueError("No fields provided for update.")
    return api_patch(f"/landscapes/{lid}", body)


def delete_landscape(landscape_id: str | None = None) -> dict:
    """Delete a landscape permanently."""
    lid = _require_landscape_id(landscape_id)
    api_delete(f"/landscapes/{lid}")
    return {"status": "deleted", "landscape_id": lid}


def copy_landscape(landscape_id: str | None = None) -> dict:
    """Copy a landscape (into another organization or as a template)."""
    lid = _require_landscape_id(landscape_id)
    return api_post(f"/landscapes/{lid}/copy")


def duplicate_landscape(landscape_id: str | None = None) -> dict:
    """Duplicate a landscape within the same organization."""
    lid = _require_landscape_id(landscape_id)
    return api_post(f"/landscapes/{lid}/duplicate")


def export_landscape(
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Start an async landscape export. Returns an export ID to poll."""
    lid = _require_landscape_id(landscape_id)
    vid = version_id or _get_default_version_id()
    return api_post(f"/landscapes/{lid}/versions/{vid}/export")


def export_status(
    export_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Check the status of an async landscape export."""
    lid = _require_landscape_id(landscape_id)
    vid = version_id or _get_default_version_id()
    return api_get(f"/landscapes/{lid}/versions/{vid}/export/{export_id}")


def import_landscape(
    data: dict,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Start an async landscape import. Returns an import ID to poll."""
    lid = _require_landscape_id(landscape_id)
    vid = version_id or _get_default_version_id()
    return api_post(f"/landscapes/{lid}/versions/{vid}/import", data)


def import_status(
    import_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Check the status of an async landscape import."""
    lid = _require_landscape_id(landscape_id)
    vid = version_id or _get_default_version_id()
    return api_get(f"/landscapes/{lid}/versions/{vid}/import/{import_id}")


def list_action_logs(
    landscape_id: str | None = None,
    performed_by: str | None = None,
    limit: int = 20,
) -> dict:
    """List recent action logs for a landscape.

    Args:
        performed_by: Filter by performer type ('user' or 'api-key').
        limit: Maximum number of logs to return.
    """
    lid = _require_landscape_id(landscape_id)
    data = api_get(f"/landscapes/{lid}/action-logs")
    logs = data.get("actionLogs", data.get("landscapeActionLogs", []))

    if performed_by:
        logs = [l for l in logs if l.get("performedBy") == performed_by]

    logs = logs[:limit]

    return {
        "count": len(logs),
        "logs": [_fmt_log(l) for l in logs],
    }


def _fmt_log(data: dict) -> dict:
    action = data.get("action", {})
    return {
        "id": data.get("id", ""),
        "action_type": action.get("type", "") if isinstance(action, dict) else str(action),
        "performed_by": data.get("performedBy", ""),
        "performed_by_id": data.get("performedById", ""),
        "performed_by_name": data.get("performedByName", ""),
        "performed_at": data.get("performedAt", ""),
    }


def search(
    query: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Search within a landscape version."""
    lid = _require_landscape_id(landscape_id)
    vid = version_id or _get_default_version_id()
    return api_get(f"/landscapes/{lid}/versions/{vid}/search", params={"q": query})
