"""Diagram management — CRUD, content, export, thumbnails, groups, ID resolution.

Diagrams visualize subsets of the architecture model. They live within
a landscape version and can be organized into diagram groups.

IcePanel has a three-layer ID system:
  1. Model object/connection IDs — canonical IDs in the model
  2. Diagram item IDs — diagram-specific IDs for positioned elements
  3. Flow step references — use diagram item IDs for originId/targetId/viaId

The resolve/lookup functions bridge these layers.
"""

from typing import Any

from cli_anything.icepanel.utils.icepanel_backend import (
    api_get,
    api_post,
    api_put,
    api_patch,
    api_delete,
    api_head,
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
    return f"/landscapes/{lid}/versions/{vid}/diagrams"


# ── Diagrams ─────────────────────────────────────────────────────

def list_diagrams(landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """List all diagrams."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(_base(lid, vid))
    diagrams = data.get("diagrams", [])
    return {"count": len(diagrams), "diagrams": [_fmt(d) for d in diagrams]}


def create_diagram(landscape_id: str | None = None, version_id: str | None = None, **kwargs) -> dict:
    """Create a new diagram."""
    lid, vid = _lv(landscape_id, version_id)
    return api_post(_base(lid, vid), {k: v for k, v in kwargs.items() if v is not None})


def get_diagram(diagram_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Get diagram details."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(f"{_base(lid, vid)}/{diagram_id}")
    return _fmt(data.get("diagram", data))


def update_diagram(diagram_id: str, landscape_id: str | None = None, version_id: str | None = None, **kwargs) -> dict:
    """Partially update a diagram."""
    lid, vid = _lv(landscape_id, version_id)
    body = {k: v for k, v in kwargs.items() if v is not None}
    if not body:
        raise ValueError("No fields provided.")
    data = api_patch(f"{_base(lid, vid)}/{diagram_id}", body)
    return data.get("diagram", data)


def delete_diagram(diagram_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Delete a diagram."""
    lid, vid = _lv(landscape_id, version_id)
    return api_delete(f"{_base(lid, vid)}/{diagram_id}")


def exists_diagram(diagram_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Check if a diagram exists (HEAD)."""
    lid, vid = _lv(landscape_id, version_id)
    result = api_head(f"{_base(lid, vid)}/{diagram_id}")
    return {"exists": result.get("status_code") == 200}


# ── Content ──────────────────────────────────────────────────────

def get_content(diagram_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Get diagram content (layout, positioned objects)."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/{diagram_id}/content")


def replace_content(diagram_id: str, content: dict, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Replace diagram content entirely (PUT)."""
    lid, vid = _lv(landscape_id, version_id)
    return api_put(f"{_base(lid, vid)}/{diagram_id}/content", content)


def update_content(diagram_id: str, content: dict, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Partially update diagram content (PATCH with $add/$update/$remove operators)."""
    lid, vid = _lv(landscape_id, version_id)
    return api_patch(f"{_base(lid, vid)}/{diagram_id}/content", content)


def add_connection_to_diagram(
    diagram_id: str,
    model_connection_id: str,
    origin_diagram_id: str,
    target_diagram_id: str,
    conn_diagram_id: str | None = None,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Add a model connection to a diagram using the $add patch operator.

    Args:
        diagram_id: The diagram to add the connection to.
        model_connection_id: The model connection ID.
        origin_diagram_id: The diagram-specific ID of the origin object.
        target_diagram_id: The diagram-specific ID of the target object.
        conn_diagram_id: Optional diagram-specific ID for the connection
                         (auto-generated if not provided).
    """
    import random
    import string
    if not conn_diagram_id:
        conn_diagram_id = "c" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))

    patch = {
        "connections": {
            "$add": {
                conn_diagram_id: {
                    "id": conn_diagram_id,
                    "modelId": model_connection_id,
                    "originId": origin_diagram_id,
                    "targetId": target_diagram_id,
                    "originConnector": "right-middle",
                    "targetConnector": "left-middle",
                    "labelPosition": 50,
                    "lineShape": "curved",
                    "points": [],
                }
            }
        }
    }
    lid, vid = _lv(landscape_id, version_id)
    update_content(diagram_id, patch, lid, vid)
    return {"diagram_connection_id": conn_diagram_id, "model_connection_id": model_connection_id}


# ── ID Resolution ────────────────────────────────────────────────

def _fetch_resolution_data(diagram_id, landscape_id=None, version_id=None):
    """Fetch diagram content, model objects, and model connections for resolution.

    Returns (diagram_content_dict, {model_id: model_obj}, {model_id: model_conn})
    """
    lid, vid = _lv(landscape_id, version_id)
    content = api_get(f"{_base(lid, vid)}/{diagram_id}/content")
    objects_data = api_get(f"/landscapes/{lid}/versions/{vid}/model/objects")
    conns_data = api_get(f"/landscapes/{lid}/versions/{vid}/model/connections")

    obj_by_id = {o["id"]: o for o in objects_data.get("modelObjects", [])}
    conn_by_id = {c["id"]: c for c in conns_data.get("modelConnections", [])}
    dc = content.get("diagramContent", content)

    return dc, obj_by_id, conn_by_id


def resolve_content(diagram_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Resolve all diagram content IDs to model object/connection names.

    Returns:
        {
            "objects": [{"diagram_id": "...", "model_id": "...", "name": "...", "type": "..."}, ...],
            "connections": [{"diagram_id": "...", "model_id": "...", "name": "...",
                           "origin": "...", "target": "..."}, ...],
        }
    """
    dc, obj_by_id, conn_by_id = _fetch_resolution_data(diagram_id, landscape_id, version_id)

    diag_conns = dc.get("connections", {})

    # Build diagram object ID → model object by reverse-mapping from connection endpoints
    diag_obj_to_model_id: dict[str, str] = {}
    for dconn in diag_conns.values():
        model_conn_id = dconn.get("modelId", "")
        model_conn = conn_by_id.get(model_conn_id)
        if model_conn:
            diag_obj_to_model_id[dconn["originId"]] = model_conn["originId"]
            diag_obj_to_model_id[dconn["targetId"]] = model_conn["targetId"]

    # Also check diagram items (some diagrams use an items dict)
    for did, item in dc.get("items", {}).items():
        mid = item.get("modelId", "")
        if mid and mid in obj_by_id:
            diag_obj_to_model_id[did] = mid

    # Build resolved objects list
    resolved_objects = []
    for diag_id, model_id in sorted(diag_obj_to_model_id.items()):
        obj = obj_by_id.get(model_id, {})
        resolved_objects.append({
            "diagram_id": diag_id,
            "model_id": model_id,
            "name": obj.get("name", "unknown"),
            "type": obj.get("type", "unknown"),
        })

    # Build resolved connections list
    resolved_conns = []
    for dcid, dconn in diag_conns.items():
        model_conn_id = dconn.get("modelId", "")
        model_conn = conn_by_id.get(model_conn_id, {})
        origin_model_id = model_conn.get("originId", "")
        target_model_id = model_conn.get("targetId", "")
        resolved_conns.append({
            "diagram_id": dcid,
            "model_id": model_conn_id,
            "name": model_conn.get("name", "unknown"),
            "origin": obj_by_id.get(origin_model_id, {}).get("name", "unknown"),
            "target": obj_by_id.get(target_model_id, {}).get("name", "unknown"),
        })

    return {
        "object_count": len(resolved_objects),
        "connection_count": len(resolved_conns),
        "objects": resolved_objects,
        "connections": resolved_conns,
    }


def lookup_diagram_id(
    diagram_id: str,
    name: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Find diagram-specific IDs for model objects/connections matching a name.

    Searches both objects and connections by substring match (case-insensitive).

    Returns:
        {
            "objects": [{"diagram_id": "...", "model_id": "...", "name": "...", "type": "..."}, ...],
            "connections": [{"diagram_id": "...", "model_id": "...", "name": "...",
                           "origin": "...", "target": "..."}, ...],
        }
    """
    resolved = resolve_content(diagram_id, landscape_id, version_id)
    search = name.lower()

    matching_objects = [
        o for o in resolved["objects"]
        if search in o["name"].lower()
    ]
    matching_conns = [
        c for c in resolved["connections"]
        if search in c["name"].lower()
        or search in c["origin"].lower()
        or search in c["target"].lower()
    ]

    return {
        "objects": matching_objects,
        "connections": matching_conns,
    }


# ── Export ───────────────────────────────────────────────────────

def export_image(diagram_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Start async diagram image export. Returns export ID to poll."""
    lid, vid = _lv(landscape_id, version_id)
    return api_post(f"{_base(lid, vid)}/{diagram_id}/export/image")


def get_export_image(diagram_id: str, export_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Get status/result of a diagram image export."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/{diagram_id}/export/image/{export_id}")


# ── Thumbnails ───────────────────────────────────────────────────

def get_thumbnail(diagram_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Get a diagram's thumbnail."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/{diagram_id}/thumbnail")


def list_thumbnails(landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """List all diagram thumbnails."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/thumbnails")


# ── Diagram Groups ──────────────────────────────────────────────

def list_groups(landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """List diagram groups."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"/landscapes/{lid}/versions/{vid}/diagram-groups")


def create_group(landscape_id: str | None = None, version_id: str | None = None, **kwargs) -> dict:
    """Create a diagram group."""
    lid, vid = _lv(landscape_id, version_id)
    return api_post(f"/landscapes/{lid}/versions/{vid}/diagram-groups",
                    {k: v for k, v in kwargs.items() if v is not None})


def get_group(group_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Get a diagram group."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(f"/landscapes/{lid}/versions/{vid}/diagram-groups/{group_id}")
    return data.get("diagramGroup", data)


def delete_group(group_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Delete a diagram group."""
    lid, vid = _lv(landscape_id, version_id)
    return api_delete(f"/landscapes/{lid}/versions/{vid}/diagram-groups/{group_id}")


def _fmt(data: dict) -> dict:
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "landscape_id": data.get("landscapeId", ""),
        "version_id": data.get("versionId", ""),
        "created_at": data.get("createdAt", ""),
        "updated_at": data.get("updatedAt", ""),
    }
