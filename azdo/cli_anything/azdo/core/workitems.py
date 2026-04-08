"""Work item CRUD operations.

Provides functions for getting, listing, creating, updating, and searching
Azure DevOps work items. All functions return plain dicts suitable for
JSON serialization or human-readable formatting.
"""

import re
from typing import Optional

from cli_anything.azdo.utils.azdo_backend import api_get, api_post, api_patch, get_org, get_project
from cli_anything.azdo.core.wiql import build_query, run_wiql


# Maximum IDs per batch request (Azure DevOps limit is 200)
BATCH_SIZE = 200


def _flatten_workitem(raw: dict, extra_fields: list[str] | None = None) -> dict:
    """Extract key fields from a raw Azure DevOps work item response.

    Resolves AssignedTo to a display name string and extracts
    parent/child IDs from relations.

    Args:
        raw: Raw work item dict from the API.
        extra_fields: Optional list of additional field reference names
            to include in the output (e.g. 'Custom.MyField').

    Returns:
        Flattened dict with human-friendly field names.
    """
    fields = raw.get("fields", {})

    # Resolve assigned_to
    assigned = fields.get("System.AssignedTo")
    if isinstance(assigned, dict):
        assigned_to = assigned.get("displayName")
    else:
        assigned_to = assigned  # None or string

    # Extract relations
    parent_id = None
    children = []
    for rel in raw.get("relations", []):
        rel_type = rel.get("rel", "")
        url = rel.get("url", "")
        # Extract ID from URL
        match = re.search(r"/workitems/(\d+)$", url, re.IGNORECASE)
        if not match:
            continue
        linked_id = int(match.group(1))

        if rel_type == "System.LinkTypes.Hierarchy-Reverse":
            parent_id = linked_id
        elif rel_type == "System.LinkTypes.Hierarchy-Forward":
            children.append(linked_id)

    result = {
        "id": raw.get("id"),
        "title": fields.get("System.Title"),
        "state": fields.get("System.State"),
        "type": fields.get("System.WorkItemType"),
        "assigned_to": assigned_to,
        "area_path": fields.get("System.AreaPath"),
        "iteration_path": fields.get("System.IterationPath"),
        "created_date": fields.get("System.CreatedDate"),
        "changed_date": fields.get("System.ChangedDate"),
        "description": fields.get("System.Description"),
        "tags": fields.get("System.Tags"),
        "parent_id": parent_id,
        "children": children,
        "rev": raw.get("rev"),
        "url": raw.get("url"),
    }

    # Include all Custom.* fields automatically
    for field_name, value in fields.items():
        if field_name.startswith("Custom."):
            result[field_name] = value

    if extra_fields:
        for field_name in extra_fields:
            result[field_name] = fields.get(field_name)

    return result


def _batch_get_workitems(ids: list[int], expand: str = "all") -> list[dict]:
    """Fetch work items in batches of up to 200.

    Args:
        ids: List of work item IDs to fetch.
        expand: Expand parameter (default: 'all').

    Returns:
        List of flattened work item dicts.
    """
    if not ids:
        return []

    results = []
    for i in range(0, len(ids), BATCH_SIZE):
        chunk = ids[i:i + BATCH_SIZE]
        id_str = ",".join(str(x) for x in chunk)
        response = api_get(
            "/wit/workitems",
            params={"ids": id_str, "$expand": expand},
        )
        for item in response.get("value", []):
            results.append(_flatten_workitem(item))

    return results


def get_workitem(
    work_item_id: int,
    extra_fields: list[str] | None = None,
) -> dict:
    """Get a single work item by ID with all fields and relations.

    Args:
        work_item_id: The work item ID.
        extra_fields: Optional list of additional field reference names
            to include in the output.

    Returns:
        Flattened work item dict.

    Raises:
        RuntimeError: If the work item is not found.
    """
    raw = api_get(
        f"/wit/workitems/{work_item_id}",
        params={"$expand": "all"},
    )
    return _flatten_workitem(raw, extra_fields=extra_fields)


def get_workitem_fields(
    work_item_id: int,
    field_names: list[str] | None = None,
) -> dict:
    """Get all raw fields for a work item, including custom fields.

    Args:
        work_item_id: The work item ID.
        field_names: Optional list of specific field names to return.
            If None, returns all fields.

    Returns:
        Dict with 'id' and 'fields' (sorted dict of field name → value).

    Raises:
        RuntimeError: If the work item is not found.
    """
    raw = api_get(
        f"/wit/workitems/{work_item_id}",
        params={"$expand": "all"},
    )
    all_fields = raw.get("fields", {})

    if field_names:
        filtered = {name: all_fields.get(name) for name in field_names}
    else:
        filtered = dict(sorted(all_fields.items()))

    return {
        "id": raw.get("id"),
        "fields": filtered,
    }


def list_workitems(
    state: Optional[str] = None,
    work_item_type: Optional[str] = None,
    assigned_to: Optional[str] = None,
    area: Optional[str] = None,
    iteration: Optional[str] = None,
    top: Optional[int] = None,
) -> list[dict]:
    """List work items matching the given filters.

    Uses WIQL to find matching IDs, then batch-fetches the details.

    Args:
        state: Filter by state.
        work_item_type: Filter by work item type.
        assigned_to: Filter by assignee ('@Me' for current user).
        area: Filter by area path.
        iteration: Filter by iteration path.
        top: Maximum number of results.

    Returns:
        List of flattened work item dicts.
    """
    project = get_project()
    query = build_query(
        project=project,
        state=state,
        work_item_type=work_item_type,
        assigned_to=assigned_to,
        area=area,
        iteration=iteration,
    )
    wi_refs = run_wiql(query, project=project, top=top)
    ids = [ref["id"] for ref in wi_refs]

    if not ids:
        return []

    return _batch_get_workitems(ids)


def search_workitems(text: str, top: Optional[int] = None) -> list[dict]:
    """Search work items by title text.

    Args:
        text: Search text (uses WIQL Contains operator).
        top: Maximum number of results.

    Returns:
        List of flattened work item dicts.
    """
    project = get_project()
    query = build_query(
        project=project,
        text_contains=text,
    )
    wi_refs = run_wiql(query, project=project, top=top)
    ids = [ref["id"] for ref in wi_refs]

    if not ids:
        return []

    return _batch_get_workitems(ids)


def get_children(work_item_id: int) -> list[dict]:
    """Get child work items of a parent.

    Args:
        work_item_id: Parent work item ID.

    Returns:
        List of flattened child work item dicts.
    """
    parent = get_workitem(work_item_id)
    child_ids = parent.get("children", [])

    if not child_ids:
        return []

    return _batch_get_workitems(child_ids)


def update_workitem(work_item_id: int, fields: dict) -> dict:
    """Update a work item's fields.

    Args:
        work_item_id: The work item ID.
        fields: Dict of field names to values (e.g. {'System.State': 'Closed'}).

    Returns:
        Flattened updated work item dict.
    """
    patch_ops = [
        {"op": "add", "path": f"/fields/{field}", "value": value}
        for field, value in fields.items()
    ]
    raw = api_patch(
        f"/wit/workitems/{work_item_id}",
        data=patch_ops,
    )
    return _flatten_workitem(raw)


def create_workitem(
    work_item_type: str,
    fields: dict,
    parent_id: Optional[int] = None,
) -> dict:
    """Create a new work item.

    Args:
        work_item_type: Work item type (e.g. 'Task', 'Bug').
        fields: Dict of field names to values.
        parent_id: Optional parent work item ID to link to.

    Returns:
        Flattened created work item dict.
    """
    patch_ops = [
        {"op": "add", "path": f"/fields/{field}", "value": value}
        for field, value in fields.items()
    ]

    if parent_id is not None:
        org = get_org()
        patch_ops.append({
            "op": "add",
            "path": "/relations/-",
            "value": {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"https://dev.azure.com/{org}/_apis/wit/workitems/{parent_id}",
            },
        })

    raw = api_post(
        f"/wit/workitems/${work_item_type}",
        data=patch_ops,
        content_type="application/json-patch+json",
    )
    return _flatten_workitem(raw)
