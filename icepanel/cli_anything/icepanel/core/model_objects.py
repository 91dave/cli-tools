"""Model object management — systems, apps, stores, actors, components, groups.

Model objects are the core architectural building blocks in IcePanel.
They live within a landscape version and can be nested (parent/child).

Types: system, app, store, actor, component, group
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
    """Resolve landscape and version IDs."""
    lid = landscape_id or _get_default_landscape_id()
    if not lid:
        raise RuntimeError("Landscape ID required. Pass --landscape-id or set default.")
    vid = version_id or _get_default_version_id()
    return lid, vid


def _base(lid: str, vid: str) -> str:
    return f"/landscapes/{lid}/versions/{vid}/model/objects"


def list_objects(
    landscape_id: str | None = None,
    version_id: str | None = None,
    name_filter: str | None = None,
    type_filter: str | None = None,
    tag_id_filter: str | None = None,
    external_filter: bool | None = None,
) -> dict:
    """List model objects with optional client-side filtering.

    Args:
        name_filter: Substring match on object name (case-insensitive).
        type_filter: Exact match on type (system, app, store, actor, component, group).
        tag_id_filter: Only objects that have this tag ID.
        external_filter: True = external only, False = internal only, None = all.
    """
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(_base(lid, vid))
    objects = data.get("modelObjects", [])

    if name_filter:
        search = name_filter.lower()
        objects = [o for o in objects if search in o.get("name", "").lower()]
    if type_filter:
        objects = [o for o in objects if o.get("type") == type_filter]
    if tag_id_filter:
        objects = [o for o in objects if tag_id_filter in o.get("tagIds", [])]
    if external_filter is not None:
        objects = [o for o in objects if o.get("external") == external_filter]

    return {"count": len(objects), "model_objects": [_fmt(o) for o in objects]}


def create_object(
    name: str,
    obj_type: str,
    parent_id: str | None = None,
    landscape_id: str | None = None,
    version_id: str | None = None,
    **kwargs,
) -> dict:
    """Create a new model object.

    Args:
        name: Object display name.
        obj_type: One of: system, app, store, actor, component, group.
        parent_id: Parent model object ID (null for root level).
        **kwargs: description, caption, external, status, icon, labels,
                  tagIds, technologyIds, teamIds, groupIds, domainId, handleId, links.
    """
    lid, vid = _lv(landscape_id, version_id)
    body: dict[str, Any] = {"name": name, "type": obj_type, "parentId": parent_id}
    for key in (
        "description", "caption", "external", "status", "icon",
        "labels", "tagIds", "technologyIds", "teamIds", "groupIds",
        "teamOnlyEditing", "domainId", "handleId", "links",
    ):
        if key in kwargs and kwargs[key] is not None:
            body[key] = kwargs[key]
    data = api_post(_base(lid, vid), body)
    return data.get("modelObject", data)


def get_object(
    object_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Get a model object by ID (expanded with domain, tags, technologies)."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(f"{_base(lid, vid)}/{object_id}")
    return _fmt(data.get("modelObject", data))


def upsert_object(
    object_id: str,
    name: str,
    obj_type: str,
    parent_id: str | None = None,
    landscape_id: str | None = None,
    version_id: str | None = None,
    **kwargs,
) -> dict:
    """Create or replace a model object by ID (idempotent PUT)."""
    lid, vid = _lv(landscape_id, version_id)
    body: dict[str, Any] = {"name": name, "type": obj_type, "parentId": parent_id}
    body.update({k: v for k, v in kwargs.items() if v is not None})
    data = api_put(f"{_base(lid, vid)}/{object_id}", body)
    return data.get("modelObject", data)


def update_object(
    object_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
    **kwargs,
) -> dict:
    """Partially update a model object."""
    lid, vid = _lv(landscape_id, version_id)
    body = {k: v for k, v in kwargs.items() if v is not None}
    if not body:
        raise ValueError("No fields provided for update.")
    data = api_patch(f"{_base(lid, vid)}/{object_id}", body)
    return data.get("modelObject", data)


def delete_object(
    object_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Delete a model object (cascades to child objects and connections)."""
    lid, vid = _lv(landscape_id, version_id)
    return api_delete(f"{_base(lid, vid)}/{object_id}")


def export_objects_csv(
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Export all model objects as CSV."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/export/csv")


def export_dependencies_json(
    object_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Export a model object's incoming/outgoing dependencies as JSON."""
    lid, vid = _lv(landscape_id, version_id)
    return api_get(f"{_base(lid, vid)}/{object_id}/dependencies/export/json")


def _fmt(data: dict) -> dict:
    """Format model object for output."""
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "type": data.get("type", ""),
        "status": data.get("status", ""),
        "parent_id": data.get("parentId"),
        "parent_ids": data.get("parentIds", []),
        "child_ids": data.get("childIds", []),
        "caption": data.get("caption", ""),
        "description": data.get("description", ""),
        "external": data.get("external", False),
        "domain_id": data.get("domainId", ""),
        "tag_ids": data.get("tagIds", []),
        "technology_ids": data.get("technologyIds", []),
        "team_ids": data.get("teamIds", []),
        "labels": data.get("labels", {}),
        "created_at": data.get("createdAt", ""),
        "updated_at": data.get("updatedAt", ""),
    }
