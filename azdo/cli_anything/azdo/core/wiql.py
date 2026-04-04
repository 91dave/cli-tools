"""WIQL query builder and executor.

Constructs WIQL (Work Item Query Language) queries from keyword arguments
and executes them against the Azure DevOps API.
"""

from typing import Optional

from cli_anything.azdo.utils.azdo_backend import api_post, get_project


def _escape_wiql_value(value: str) -> str:
    """Escape single quotes in WIQL values by doubling them."""
    return value.replace("'", "''")


def build_query(
    project: str,
    state: Optional[str] = None,
    work_item_type: Optional[str] = None,
    assigned_to: Optional[str] = None,
    area: Optional[str] = None,
    iteration: Optional[str] = None,
    text_contains: Optional[str] = None,
    order_by: str = "[System.ChangedDate] DESC",
) -> str:
    """Build a WIQL query string from keyword arguments.

    Args:
        project: Azure DevOps project name.
        state: Filter by work item state (e.g. 'Active', 'Closed').
        work_item_type: Filter by type (e.g. 'Bug', 'Task').
        assigned_to: Filter by assigned person. Use '@Me' for current user.
        area: Filter by area path.
        iteration: Filter by iteration path.
        text_contains: Search text in title.
        order_by: ORDER BY clause. Default: [System.ChangedDate] DESC.

    Returns:
        WIQL query string.
    """
    conditions = [
        f"[System.TeamProject] = '{_escape_wiql_value(project)}'"
    ]

    if state:
        conditions.append(f"[System.State] = '{_escape_wiql_value(state)}'")

    if work_item_type:
        conditions.append(f"[System.WorkItemType] = '{_escape_wiql_value(work_item_type)}'")

    if assigned_to:
        if assigned_to == "@Me":
            conditions.append("[System.AssignedTo] = @Me")
        else:
            conditions.append(f"[System.AssignedTo] = '{_escape_wiql_value(assigned_to)}'")

    if area:
        conditions.append(f"[System.AreaPath] = '{_escape_wiql_value(area)}'")

    if iteration:
        conditions.append(f"[System.IterationPath] = '{_escape_wiql_value(iteration)}'")

    if text_contains:
        conditions.append(
            f"[System.Title] Contains '{_escape_wiql_value(text_contains)}'"
        )

    where_clause = " AND ".join(conditions)

    query = (
        "SELECT [System.Id], [System.Title], [System.State], "
        "[System.WorkItemType], [System.AssignedTo], [System.ChangedDate] "
        f"FROM WorkItems WHERE {where_clause} "
        f"ORDER BY {order_by}"
    )

    return query


def run_wiql(
    query: str,
    project: Optional[str] = None,
    top: Optional[int] = None,
) -> list[dict]:
    """Execute a WIQL query and return the list of work item references.

    Args:
        query: WIQL query string.
        project: Project override.
        top: Maximum number of results.

    Returns:
        List of dicts with 'id' and 'url' keys.
    """
    params = {}
    if top is not None:
        params["$top"] = top

    kwargs = {}
    if project:
        kwargs["project"] = project

    result = api_post(
        "/wit/wiql",
        data={"query": query},
        params=params,
        **kwargs,
    )

    return result.get("workItems", [])


def get_my_workitems(project: Optional[str] = None) -> list[dict]:
    """Get active work items assigned to the current user.

    Returns:
        List of work item references from WIQL.
    """
    proj = project or get_project()
    query = build_query(project=proj, assigned_to="@Me", state="Active")
    return run_wiql(query, project=proj)
