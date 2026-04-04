"""Flow management — sequence diagrams showing interactions between objects.

Flows describe step-by-step interactions between model objects. They can
be exported as Mermaid diagrams, code, or plain text.

Flow steps use diagram-specific IDs (not model IDs) for originId/targetId/viaId.
The optional name resolution feature bridges this by looking up names in
diagram content.
"""

import json as json_mod
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
    return f"/landscapes/{lid}/versions/{vid}/flows"


def list_flows(landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """List all flows."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(_base(lid, vid))
    flows = data.get("flows", [])
    return {"count": len(flows), "flows": [_fmt(f) for f in flows]}


def get_flow(flow_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Get flow details."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(f"{_base(lid, vid)}/{flow_id}")
    return _fmt(data.get("flow", data))


def delete_flow(flow_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Delete a flow."""
    lid, vid = _lv(landscape_id, version_id)
    return api_delete(f"{_base(lid, vid)}/{flow_id}")


def exists_flow(flow_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Check if a flow exists."""
    lid, vid = _lv(landscape_id, version_id)
    result = api_head(f"{_base(lid, vid)}/{flow_id}")
    return {"exists": result.get("status_code") == 200}


# ── Flow Creation ────────────────────────────────────────────────

def create_flow(
    name: str,
    diagram_id: str,
    steps: list | dict | None = None,
    resolve_names: bool = False,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Create a flow with optional step definitions.

    Args:
        name: Flow name.
        diagram_id: Diagram to attach the flow to.
        steps: Either a list of step dicts (auto-assigned IDs) or a dict of
               {step_id: step_dict}. If a list, each dict should have at minimum
               'type' and 'description'. For outgoing steps: 'origin'/'originId',
               'target'/'targetId', optionally 'via'/'viaId'.
        resolve_names: If True, 'origin', 'target', 'via' values are treated as
                       model object/connection names and resolved via diagram content.
        landscape_id: Landscape ID (uses default if not provided).
        version_id: Version ID (uses default if not provided).
    """
    lid, vid = _lv(landscape_id, version_id)

    if steps is None:
        steps = {}
    elif isinstance(steps, list):
        steps = build_steps_from_list(steps)

    if resolve_names and steps:
        steps = _resolve_step_names(steps, diagram_id, lid, vid)

    body = {"name": name, "diagramId": diagram_id, "steps": steps}
    data = api_post(_base(lid, vid), body)
    return data.get("flow", data)


def build_steps_from_list(step_list: list) -> dict:
    """Convert a list of step definitions into the {id: step} dict the API expects.

    Auto-generates step IDs and handles alternate-path/child step nesting.

    Each step dict in the list should have:
        - type: introduction|outgoing|self-action|alternate-path
        - description: step description
        - origin/originId: origin object (name or diagram ID)
        - target/targetId: target object (name or diagram ID)
        - via/viaId: connection (name or diagram ID)
        - parent_path: name of the alternate-path this step belongs to (for child steps)
        - paths: list of {"name": "..."} for alternate-path steps
        - detailedDescription: optional detailed text
    """
    if not step_list:
        raise ValueError("Steps list cannot be empty.")

    steps = {}
    path_name_to_id = {}
    main_index = 0
    child_counters: dict[str, int] = {}

    for item in step_list:
        stype = item.get("type", "outgoing")
        parent_path_name = item.get("parent_path")

        if parent_path_name:
            # Child step inside an alternate path
            path_id = path_name_to_id.get(parent_path_name)
            if not path_id:
                raise ValueError(
                    f"parent_path '{parent_path_name}' not found. "
                    f"Define the alternate-path step first."
                )
            child_idx = child_counters.get(path_id, 0)
            sid = f"s{main_index - 1}a{child_idx}" if child_idx > 0 else f"s{main_index - 1}a"
            child_counters[path_id] = child_idx + 1
            step = _build_step(sid, child_idx, item, parent_id=path_id)
        else:
            sid = f"s{main_index}"
            step = _build_step(sid, main_index, item)
            main_index += 1

            # Register paths for alternate-path steps
            if stype == "alternate-path" and item.get("paths"):
                step["paths"] = {}
                for pidx, p in enumerate(item["paths"]):
                    pid = f"p{len(path_name_to_id) + 1}"
                    path_name_to_id[p["name"]] = pid
                    step["paths"][pid] = {"id": pid, "name": p["name"], "index": pidx}

        steps[sid] = step

    return steps


def _build_step(sid: str, index: int, item: dict, parent_id: str | None = None) -> dict:
    """Build a single step dict from a user-provided item."""
    step = {
        "id": sid,
        "index": index,
        "type": item.get("type", "outgoing"),
        "description": item.get("description", ""),
        "originId": item.get("originId") or item.get("origin"),
        "targetId": item.get("targetId") or item.get("target"),
        "viaId": item.get("viaId") or item.get("via"),
        "parentId": parent_id,
        "paths": item.get("paths") if isinstance(item.get("paths"), dict) else None,
        "flowId": None,
    }
    if item.get("detailedDescription"):
        step["detailedDescription"] = item["detailedDescription"]
    return step


def _resolve_step_names(steps: dict, diagram_id: str, lid: str, vid: str) -> dict:
    """Resolve human-readable names in step originId/targetId/viaId to diagram IDs."""
    from cli_anything.icepanel.core.diagrams import resolve_content

    resolved = resolve_content(diagram_id, lid, vid)

    # Build lookup maps
    obj_name_to_diag = {}
    for o in resolved["objects"]:
        name_lower = o["name"].lower()
        obj_name_to_diag[name_lower] = o["diagram_id"]

    conn_name_to_diag = {}
    for c in resolved["connections"]:
        name_lower = c["name"].lower()
        conn_name_to_diag[name_lower] = c["diagram_id"]
        # Also index by "origin → target" pattern
        pair_key = f"{c['origin'].lower()} → {c['target'].lower()}"
        conn_name_to_diag[pair_key] = c["diagram_id"]

    for step in steps.values():
        for field in ("originId", "targetId"):
            val = step.get(field)
            if val and val.lower() in obj_name_to_diag:
                step[field] = obj_name_to_diag[val.lower()]

        via = step.get("viaId")
        if via and via.lower() in conn_name_to_diag:
            step["viaId"] = conn_name_to_diag[via.lower()]

    return steps


# ── Flow Update (patch operators) ────────────────────────────────

def update_flow(flow_id: str, landscape_id: str | None = None, version_id: str | None = None, **kwargs) -> dict:
    """Update top-level flow properties (name, diagramId, etc.).

    Does NOT handle step modifications — use add/update/remove_flow_steps for that.
    """
    lid, vid = _lv(landscape_id, version_id)
    body = {k: v for k, v in kwargs.items() if v is not None}
    if not body:
        raise ValueError("No fields provided.")
    data = api_patch(f"{_base(lid, vid)}/{flow_id}", body)
    return data.get("flow", data)


def add_flow_steps(
    flow_id: str,
    steps: dict,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Add steps to an existing flow using the $add patch operator.

    Args:
        flow_id: The flow to add steps to.
        steps: Dict of {step_id: step_dict} to add.
    """
    lid, vid = _lv(landscape_id, version_id)
    body = {"steps": {"$add": steps}}
    data = api_patch(f"{_base(lid, vid)}/{flow_id}", body)
    return data.get("flow", data)


def update_flow_steps(
    flow_id: str,
    steps: dict,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Update existing steps using the $update patch operator.

    Args:
        flow_id: The flow to update.
        steps: Dict of {step_id: {fields to update}}.
    """
    lid, vid = _lv(landscape_id, version_id)
    body = {"steps": {"$update": steps}}
    data = api_patch(f"{_base(lid, vid)}/{flow_id}", body)
    return data.get("flow", data)


def remove_flow_steps(
    flow_id: str,
    step_ids: list,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Remove steps by ID using the $remove patch operator.

    Args:
        flow_id: The flow to remove steps from.
        step_ids: List of step IDs to remove.
    """
    lid, vid = _lv(landscape_id, version_id)
    body = {"steps": {"$remove": step_ids}}
    data = api_patch(f"{_base(lid, vid)}/{flow_id}", body)
    return data.get("flow", data)


# ── Export ───────────────────────────────────────────────────────

def export_mermaid(flow_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Export a flow as Mermaid diagram syntax."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/{flow_id}/export/mermaid")


def export_code(flow_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Export a flow as code."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/{flow_id}/export/code")


def export_text(flow_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Export a flow as plain text description."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/{flow_id}/export/text")


# ── Thumbnails ───────────────────────────────────────────────────

def get_thumbnail(flow_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Get a flow's thumbnail."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/{flow_id}/thumbnail")


def list_thumbnails(landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """List all flow thumbnails."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/thumbnails")


def _fmt(data: dict) -> dict:
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "landscape_id": data.get("landscapeId", ""),
        "version_id": data.get("versionId", ""),
        "steps": data.get("steps", []),
        "created_at": data.get("createdAt", ""),
        "updated_at": data.get("updatedAt", ""),
    }
