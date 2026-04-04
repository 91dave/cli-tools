"""Tag and tag group management.

Tags categorize model objects and connections. Organized into tag groups.
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


# ── Tags ─────────────────────────────────────────────────────────

def list_tags(landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """List all tags."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(f"/landscapes/{lid}/versions/{vid}/tags")
    tags = data.get("tags", [])
    return {"count": len(tags), "tags": [_fmt_tag(t) for t in tags]}


def create_tag(
    name: str, color: str, group_id: str, index: int = 0,
    landscape_id: str | None = None, version_id: str | None = None, **kwargs,
) -> dict:
    """Create a tag."""
    lid, vid = _lv(landscape_id, version_id)
    body: dict[str, Any] = {"name": name, "color": color, "groupId": group_id, "index": index}
    body.update({k: v for k, v in kwargs.items() if v is not None})
    data = api_post(f"/landscapes/{lid}/versions/{vid}/tags", body)
    return data.get("tag", data)


def get_tag(tag_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Get a tag by ID."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(f"/landscapes/{lid}/versions/{vid}/tags/{tag_id}")
    return _fmt_tag(data.get("tag", data))


def update_tag(tag_id: str, landscape_id: str | None = None, version_id: str | None = None, **kwargs) -> dict:
    """Partially update a tag."""
    lid, vid = _lv(landscape_id, version_id)
    body = {k: v for k, v in kwargs.items() if v is not None}
    if not body:
        raise ValueError("No fields provided.")
    data = api_patch(f"/landscapes/{lid}/versions/{vid}/tags/{tag_id}", body)
    return data.get("tag", data)


def delete_tag(tag_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Delete a tag."""
    lid, vid = _lv(landscape_id, version_id)
    return api_delete(f"/landscapes/{lid}/versions/{vid}/tags/{tag_id}")


# ── Tag Groups ───────────────────────────────────────────────────

def list_tag_groups(landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """List all tag groups."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(f"/landscapes/{lid}/versions/{vid}/tag-groups")
    groups = data.get("tagGroups", [])
    return {"count": len(groups), "tag_groups": groups}


def create_tag_group(
    name: str, icon: str, index: int = 0,
    landscape_id: str | None = None, version_id: str | None = None, **kwargs,
) -> dict:
    """Create a tag group."""
    lid, vid = _lv(landscape_id, version_id)
    body: dict[str, Any] = {"name": name, "icon": icon, "index": index}
    body.update({k: v for k, v in kwargs.items() if v is not None})
    data = api_post(f"/landscapes/{lid}/versions/{vid}/tag-groups", body)
    return data.get("tagGroup", data)


def get_tag_group(group_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Get a tag group."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(f"/landscapes/{lid}/versions/{vid}/tag-groups/{group_id}")
    return data.get("tagGroup", data)


def delete_tag_group(group_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Delete a tag group."""
    lid, vid = _lv(landscape_id, version_id)
    return api_delete(f"/landscapes/{lid}/versions/{vid}/tag-groups/{group_id}")


def get_tagged_objects(
    tag_id: str,
    landscape_id: str | None = None,
    version_id: str | None = None,
) -> dict:
    """Get full details of all model objects tagged with a given tag."""
    lid, vid = _lv(landscape_id, version_id)
    # Get the tag to find its object IDs
    tag_data = api_get(f"/landscapes/{lid}/versions/{vid}/tags/{tag_id}")
    tag = tag_data.get("tag", tag_data)
    object_ids = set(tag.get("modelObjectIds", []))

    if not object_ids:
        return {"tag_name": tag.get("name", ""), "count": 0, "objects": []}

    # Fetch all objects and filter to tagged ones
    from cli_anything.icepanel.core.model_objects import list_objects, _fmt
    all_data = api_get(f"/landscapes/{lid}/versions/{vid}/model/objects")
    tagged = [_fmt(o) for o in all_data.get("modelObjects", []) if o["id"] in object_ids]

    return {
        "tag_name": tag.get("name", ""),
        "count": len(tagged),
        "objects": tagged,
    }


def _fmt_tag(data: dict) -> dict:
    return {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "color": data.get("color", ""),
        "group_id": data.get("groupId", ""),
        "index": data.get("index", 0),
        "model_object_ids": data.get("modelObjectIds", []),
        "model_connection_ids": data.get("modelConnectionIds", []),
    }
