"""Model connection management — links between model objects.

Connections represent relationships (API calls, data flows, dependencies)
between model objects in a landscape version.
"""

from typing import Any

from cli_anything.icepanel.utils.icepanel_backend import (
    api_get,
    api_post,
    api_put,
    api_patch,
    api_delete,
    _get_default_landscape_id,
    _get_default_version_id,
)


def _lv(landscape_id: str | None, version_id: str | None) -> tuple[str, str]:
    lid = landscape_id or _get_default_landscape_id()
    if not lid:
        raise RuntimeError("Landscape ID required.")
    vid = version_id or _get_default_version_id()
    return lid, vid


def _base(lid: str, vid: str) -> str:
    return f"/landscapes/{lid}/versions/{vid}/model/connections"


def list_connections(
    landscape_id: str | None = None,
    version_id: str | None = None,
    name_filter: str | None = None,
    origin_filter: str | None = None,
    target_filter: str | None = None,
) -> dict:
    """List model connections with optional client-side filtering.

    Args:
        name_filter: Substring match on connection name (case-insensitive).
        origin_filter: Filter by origin model object ID.
        target_filter: Filter by target model object ID.
    """
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(_base(lid, vid))
    conns = data.get("modelConnections", [])

    if name_filter:
        search = name_filter.lower()
        conns = [c for c in conns if search in c.get("name", "").lower()]
    if origin_filter:
        conns = [c for c in conns if c.get("originId") == origin_filter]
    if target_filter:
        conns = [c for c in conns if c.get("targetId") == target_filter]

    return {"count": len(conns), "model_connections": [_fmt(c) for c in conns]}


def create_connection(
    origin_id: str,
    target_id: str,
    name: str = "",
    direction: str = "outgoing",
    landscape_id: str | None = None,
    version_id: str | None = None,
    **kwargs,
) -> dict:
    """Create a connection between two model objects.

    Args:
        origin_id: Source model object ID.
        target_id: Target model object ID.
        name: Connection label/name.
        direction: Connection direction (default: 'outgoing'). Required by API.
        **kwargs: description, status, tagIds, technologyIds,
                  viaId, labels, links, handleId.
    """
    lid, vid = _lv(landscape_id, version_id)
    body: dict[str, Any] = {
        "originId": origin_id, "targetId": target_id,
        "name": name, "direction": direction,
    }
    for key in ("description", "status", "tagIds",
                "technologyIds", "viaId", "labels", "links", "handleId"):
        if key in kwargs and kwargs[key] is not None:
            body[key] = kwargs[key]
    data = api_post(_base(lid, vid), body)
    return data.get("modelConnection", data)


def get_connection(
    connection_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Get a connection by ID."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(f"{_base(lid, vid)}/{connection_id}")
    return _fmt(data.get("modelConnection", data))


def upsert_connection(
    connection_id: str,
    origin_id: str,
    target_id: str,
    name: str = "",
    landscape_id: str | None = None,
    version_id: str | None = None,
    **kwargs,
) -> dict:
    """Create or replace a connection by ID (idempotent PUT)."""
    lid, vid = _lv(landscape_id, version_id)
    body: dict[str, Any] = {"originId": origin_id, "targetId": target_id, "name": name}
    body.update({k: v for k, v in kwargs.items() if v is not None})
    data = api_put(f"{_base(lid, vid)}/{connection_id}", body)
    return data.get("modelConnection", data)


def update_connection(
    connection_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
    **kwargs,
) -> dict:
    """Partially update a connection."""
    lid, vid = _lv(landscape_id, version_id)
    body = {k: v for k, v in kwargs.items() if v is not None}
    if not body:
        raise ValueError("No fields provided for update.")
    data = api_patch(f"{_base(lid, vid)}/{connection_id}", body)
    return data.get("modelConnection", data)


def delete_connection(
    connection_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Delete a connection."""
    lid, vid = _lv(landscape_id, version_id)
    return api_delete(f"{_base(lid, vid)}/{connection_id}")


def generate_description(
    connection_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Generate an AI description for a connection."""
    lid, vid = _lv(landscape_id, version_id)
    return api_post(f"{_base(lid, vid)}/{connection_id}/generate-description")


def export_csv(
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Export all connections as CSV."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/export/csv")


def _fmt(data: dict) -> dict:
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "origin_id": data.get("originId", ""),
        "target_id": data.get("targetId", ""),
        "direction": data.get("direction"),
        "description": data.get("description", ""),
        "status": data.get("status", ""),
        "via_id": data.get("viaId"),
        "tag_ids": data.get("tagIds", []),
        "technology_ids": data.get("technologyIds", []),
        "created_at": data.get("createdAt", ""),
        "updated_at": data.get("updatedAt", ""),
    }
