"""Tests for workitems module — CRUD and batch operations."""

import json
from unittest.mock import patch, MagicMock, call

import pytest

from cli_anything.azdo.core.workitems import (
    get_workitem,
    list_workitems,
    search_workitems,
    get_children,
    update_workitem,
    create_workitem,
    _flatten_workitem,
    _batch_get_workitems,
)


# ── Sample API responses ─────────────────────────────────────────

SAMPLE_WORKITEM = {
    "id": 123,
    "rev": 5,
    "fields": {
        "System.Id": 123,
        "System.Title": "Fix login bug",
        "System.State": "Active",
        "System.WorkItemType": "Bug",
        "System.AssignedTo": {
            "displayName": "Dave Arthur",
            "uniqueName": "dave@example.com",
        },
        "System.AreaPath": "Technology\\Platform",
        "System.IterationPath": "Technology\\2026\\Q1",
        "System.CreatedDate": "2026-01-15T10:30:00Z",
        "System.ChangedDate": "2026-03-20T14:00:00Z",
        "System.Description": "<p>Login fails intermittently</p>",
        "System.Tags": "bug; urgent",
    },
    "relations": [
        {
            "rel": "System.LinkTypes.Hierarchy-Reverse",
            "url": "https://dev.azure.com/MyOrg/_apis/wit/workitems/100",
            "attributes": {"name": "Parent"},
        },
        {
            "rel": "System.LinkTypes.Hierarchy-Forward",
            "url": "https://dev.azure.com/MyOrg/_apis/wit/workitems/201",
            "attributes": {"name": "Child"},
        },
        {
            "rel": "System.LinkTypes.Hierarchy-Forward",
            "url": "https://dev.azure.com/MyOrg/_apis/wit/workitems/202",
            "attributes": {"name": "Child"},
        },
    ],
    "url": "https://dev.azure.com/MyOrg/_apis/wit/workitems/123",
}

SAMPLE_WORKITEM_NO_RELATIONS = {
    "id": 456,
    "rev": 1,
    "fields": {
        "System.Id": 456,
        "System.Title": "Simple task",
        "System.State": "New",
        "System.WorkItemType": "Task",
        "System.AssignedTo": None,
        "System.AreaPath": "Technology",
        "System.IterationPath": "Technology",
        "System.CreatedDate": "2026-04-01T09:00:00Z",
        "System.ChangedDate": "2026-04-01T09:00:00Z",
        "System.Description": "",
        "System.Tags": "",
    },
    "url": "https://dev.azure.com/MyOrg/_apis/wit/workitems/456",
}


# ── TestFlattenWorkitem ──────────────────────────────────────────

class TestFlattenWorkitem:

    def test_flatten_extracts_key_fields(self):
        result = _flatten_workitem(SAMPLE_WORKITEM)
        assert result["id"] == 123
        assert result["title"] == "Fix login bug"
        assert result["state"] == "Active"
        assert result["type"] == "Bug"
        assert result["assigned_to"] == "Dave Arthur"
        assert result["area_path"] == "Technology\\Platform"
        assert result["iteration_path"] == "Technology\\2026\\Q1"
        assert result["tags"] == "bug; urgent"

    def test_flatten_extracts_relations(self):
        result = _flatten_workitem(SAMPLE_WORKITEM)
        assert result["parent_id"] == 100
        assert result["children"] == [201, 202]

    def test_flatten_no_relations(self):
        result = _flatten_workitem(SAMPLE_WORKITEM_NO_RELATIONS)
        assert result["parent_id"] is None
        assert result["children"] == []

    def test_flatten_unassigned(self):
        result = _flatten_workitem(SAMPLE_WORKITEM_NO_RELATIONS)
        assert result["assigned_to"] is None


# ── TestGetWorkitem ──────────────────────────────────────────────

class TestGetWorkitem:

    @patch("cli_anything.azdo.core.workitems.api_get")
    def test_get_workitem_returns_formatted(self, mock_get):
        mock_get.return_value = SAMPLE_WORKITEM
        result = get_workitem(123)
        mock_get.assert_called_once_with(
            "/wit/workitems/123",
            params={"$expand": "all"},
        )
        assert result["id"] == 123
        assert result["title"] == "Fix login bug"
        assert result["assigned_to"] == "Dave Arthur"

    @patch("cli_anything.azdo.core.workitems.api_get")
    def test_get_workitem_extracts_relations(self, mock_get):
        mock_get.return_value = SAMPLE_WORKITEM
        result = get_workitem(123)
        assert result["parent_id"] == 100
        assert result["children"] == [201, 202]

    @patch("cli_anything.azdo.core.workitems.api_get")
    def test_get_workitem_missing_returns_error(self, mock_get):
        mock_get.side_effect = RuntimeError("Azure DevOps API GET /wit/workitems/99999 → 404: Not found")
        with pytest.raises(RuntimeError, match="404"):
            get_workitem(99999)


# ── TestBatchGetWorkitems ────────────────────────────────────────

class TestBatchGetWorkitems:

    @patch("cli_anything.azdo.core.workitems.api_get")
    def test_batch_single_chunk(self, mock_get):
        mock_get.return_value = {"value": [SAMPLE_WORKITEM]}
        result = _batch_get_workitems([123])
        assert len(result) == 1
        assert result[0]["id"] == 123

    @patch("cli_anything.azdo.core.workitems.api_get")
    def test_batch_over_200_chunks(self, mock_get):
        # 250 IDs should result in 2 API calls
        ids = list(range(1, 251))
        mock_get.side_effect = [
            {"value": [{"id": i, "fields": {"System.Id": i, "System.Title": f"Item {i}", "System.State": "Active", "System.WorkItemType": "Task", "System.AssignedTo": None, "System.AreaPath": "Tech", "System.IterationPath": "Tech", "System.CreatedDate": "", "System.ChangedDate": "", "System.Description": "", "System.Tags": ""}} for i in range(1, 201)]},
            {"value": [{"id": i, "fields": {"System.Id": i, "System.Title": f"Item {i}", "System.State": "Active", "System.WorkItemType": "Task", "System.AssignedTo": None, "System.AreaPath": "Tech", "System.IterationPath": "Tech", "System.CreatedDate": "", "System.ChangedDate": "", "System.Description": "", "System.Tags": ""}} for i in range(201, 251)]},
        ]
        result = _batch_get_workitems(ids)
        assert len(result) == 250
        assert mock_get.call_count == 2

    @patch("cli_anything.azdo.core.workitems.api_get")
    def test_batch_empty_ids(self, mock_get):
        result = _batch_get_workitems([])
        assert result == []
        mock_get.assert_not_called()


# ── TestListWorkitems ────────────────────────────────────────────

class TestListWorkitems:

    @patch("cli_anything.azdo.core.workitems._batch_get_workitems")
    @patch("cli_anything.azdo.core.workitems.run_wiql")
    @patch("cli_anything.azdo.core.workitems.get_project")
    def test_list_calls_wiql_then_batch(self, mock_project, mock_wiql, mock_batch):
        mock_project.return_value = "Technology"
        mock_wiql.return_value = [{"id": 1}, {"id": 2}]
        mock_batch.return_value = [
            {"id": 1, "title": "Item 1"},
            {"id": 2, "title": "Item 2"},
        ]
        result = list_workitems(state="Active")
        mock_wiql.assert_called_once()
        mock_batch.assert_called_once_with([1, 2])
        assert len(result) == 2

    @patch("cli_anything.azdo.core.workitems._batch_get_workitems")
    @patch("cli_anything.azdo.core.workitems.run_wiql")
    @patch("cli_anything.azdo.core.workitems.get_project")
    def test_list_empty_results(self, mock_project, mock_wiql, mock_batch):
        mock_project.return_value = "Technology"
        mock_wiql.return_value = []
        result = list_workitems()
        mock_batch.assert_not_called()
        assert result == []


# ── TestSearchWorkitems ──────────────────────────────────────────

class TestSearchWorkitems:

    @patch("cli_anything.azdo.core.workitems._batch_get_workitems")
    @patch("cli_anything.azdo.core.workitems.run_wiql")
    @patch("cli_anything.azdo.core.workitems.get_project")
    def test_search_builds_contains_query(self, mock_project, mock_wiql, mock_batch):
        mock_project.return_value = "Technology"
        mock_wiql.return_value = [{"id": 10}]
        mock_batch.return_value = [{"id": 10, "title": "Login fix"}]
        result = search_workitems("login")
        query = mock_wiql.call_args[0][0]
        assert "Contains" in query
        assert "login" in query


# ── TestGetChildren ──────────────────────────────────────────────

class TestGetChildren:

    @patch("cli_anything.azdo.core.workitems._batch_get_workitems")
    @patch("cli_anything.azdo.core.workitems.api_get")
    def test_get_children_follows_relations(self, mock_get, mock_batch):
        mock_get.return_value = SAMPLE_WORKITEM
        mock_batch.return_value = [
            {"id": 201, "title": "Child 1"},
            {"id": 202, "title": "Child 2"},
        ]
        result = get_children(123)
        mock_batch.assert_called_once_with([201, 202])
        assert len(result) == 2

    @patch("cli_anything.azdo.core.workitems._batch_get_workitems")
    @patch("cli_anything.azdo.core.workitems.api_get")
    def test_get_children_no_children(self, mock_get, mock_batch):
        mock_get.return_value = SAMPLE_WORKITEM_NO_RELATIONS
        result = get_children(456)
        mock_batch.assert_not_called()
        assert result == []


# ── TestUpdateWorkitem ───────────────────────────────────────────

class TestUpdateWorkitem:

    @patch("cli_anything.azdo.core.workitems.api_patch")
    def test_update_builds_json_patch(self, mock_patch):
        mock_patch.return_value = SAMPLE_WORKITEM
        update_workitem(123, {"System.State": "Closed"})
        call_args = mock_patch.call_args
        assert call_args[0][0] == "/wit/workitems/123"
        patch_body = call_args[1]["data"]
        assert len(patch_body) == 1
        assert patch_body[0] == {
            "op": "add",
            "path": "/fields/System.State",
            "value": "Closed",
        }

    @patch("cli_anything.azdo.core.workitems.api_patch")
    def test_update_multiple_fields(self, mock_patch):
        mock_patch.return_value = SAMPLE_WORKITEM
        update_workitem(123, {
            "System.State": "Closed",
            "System.Title": "Updated title",
        })
        patch_body = mock_patch.call_args[1]["data"]
        assert len(patch_body) == 2
        fields = {op["path"] for op in patch_body}
        assert "/fields/System.State" in fields
        assert "/fields/System.Title" in fields


# ── TestCreateWorkitem ───────────────────────────────────────────

class TestCreateWorkitem:

    @patch("cli_anything.azdo.core.workitems.api_post")
    @patch("cli_anything.azdo.core.workitems.get_project")
    def test_create_builds_json_patch(self, mock_project, mock_post):
        mock_project.return_value = "Technology"
        mock_post.return_value = SAMPLE_WORKITEM
        create_workitem("Task", {"System.Title": "New task"})
        call_args = mock_post.call_args
        assert call_args[0][0] == "/wit/workitems/$Task"
        patch_body = call_args[1]["data"]
        assert any(
            op["path"] == "/fields/System.Title" and op["value"] == "New task"
            for op in patch_body
        )

    @patch("cli_anything.azdo.core.workitems.get_org")
    @patch("cli_anything.azdo.core.workitems.api_post")
    @patch("cli_anything.azdo.core.workitems.get_project")
    def test_create_with_parent(self, mock_project, mock_post, mock_org):
        mock_project.return_value = "Technology"
        mock_org.return_value = "AMDigitalTech"
        mock_post.return_value = SAMPLE_WORKITEM
        create_workitem("Task", {"System.Title": "Child task"}, parent_id=100)
        patch_body = mock_post.call_args[1]["data"]
        relation_ops = [op for op in patch_body if op["path"] == "/relations/-"]
        assert len(relation_ops) == 1
        assert relation_ops[0]["value"]["rel"] == "System.LinkTypes.Hierarchy-Reverse"
        assert "100" in relation_ops[0]["value"]["url"]

    @patch("cli_anything.azdo.core.workitems.api_post")
    @patch("cli_anything.azdo.core.workitems.get_project")
    def test_create_url_includes_type(self, mock_project, mock_post):
        mock_project.return_value = "Technology"
        mock_post.return_value = SAMPLE_WORKITEM
        create_workitem("Bug", {"System.Title": "A bug"})
        assert mock_post.call_args[0][0] == "/wit/workitems/$Bug"

    @patch("cli_anything.azdo.core.workitems.api_post")
    @patch("cli_anything.azdo.core.workitems.get_project")
    def test_create_uses_json_patch_content_type(self, mock_project, mock_post):
        mock_project.return_value = "Technology"
        mock_post.return_value = SAMPLE_WORKITEM
        create_workitem("Task", {"System.Title": "Test"})
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs.get("content_type") == "application/json-patch+json"
