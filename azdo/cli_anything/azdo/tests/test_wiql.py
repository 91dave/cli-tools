"""Tests for wiql module — WIQL query building and execution."""

import json
from unittest.mock import patch, MagicMock

import pytest

from cli_anything.azdo.core.wiql import build_query, run_wiql, get_my_workitems


class TestBuildQuery:

    def test_build_query_defaults(self):
        q = build_query(project="Technology")
        assert "SELECT" in q
        assert "FROM WorkItems" in q
        assert "[System.TeamProject] = 'Technology'" in q

    def test_build_query_with_state(self):
        q = build_query(project="Technology", state="Active")
        assert "[System.State] = 'Active'" in q

    def test_build_query_with_type(self):
        q = build_query(project="Technology", work_item_type="Bug")
        assert "[System.WorkItemType] = 'Bug'" in q

    def test_build_query_with_assigned_to(self):
        q = build_query(project="Technology", assigned_to="Dave Arthur")
        assert "[System.AssignedTo] = 'Dave Arthur'" in q

    def test_build_query_with_assigned_to_me(self):
        q = build_query(project="Technology", assigned_to="@Me")
        assert "[System.AssignedTo] = @Me" in q
        # Should NOT have quotes around @Me
        assert "'@Me'" not in q

    def test_build_query_with_area(self):
        q = build_query(project="Technology", area="Technology\\TeamName")
        assert "[System.AreaPath]" in q
        assert "Technology\\TeamName" in q

    def test_build_query_with_iteration(self):
        q = build_query(project="Technology", iteration="Technology\\2026\\Q1")
        assert "[System.IterationPath]" in q
        assert "Technology\\2026\\Q1" in q

    def test_build_query_multiple_filters(self):
        q = build_query(
            project="Technology",
            state="Active",
            work_item_type="Task",
            assigned_to="Dave Arthur",
        )
        assert "[System.State] = 'Active'" in q
        assert "[System.WorkItemType] = 'Task'" in q
        assert "[System.AssignedTo] = 'Dave Arthur'" in q
        # All joined by AND
        assert q.count("AND") >= 3  # project + state + type + assigned

    def test_build_query_escapes_single_quotes(self):
        q = build_query(project="Technology", assigned_to="O'Brien")
        assert "O''Brien" in q

    def test_build_query_order_by(self):
        q = build_query(project="Technology")
        assert "ORDER BY [System.ChangedDate] DESC" in q

    def test_build_query_top(self):
        # top is passed as API param, not in WIQL — build_query returns just WIQL
        q = build_query(project="Technology")
        # Should not have LIMIT or TOP in WIQL itself
        assert "LIMIT" not in q.upper()

    def test_get_my_query(self):
        q = build_query(project="Technology", assigned_to="@Me", state="Active")
        assert "[System.AssignedTo] = @Me" in q
        assert "[System.State] = 'Active'" in q


class TestRunWiql:

    @patch("cli_anything.azdo.core.wiql.api_post")
    def test_run_wiql_posts_query(self, mock_post):
        mock_post.return_value = {"workItems": [{"id": 1}, {"id": 2}]}
        result = run_wiql("SELECT [System.Id] FROM WorkItems", project="Technology")
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "/wit/wiql"
        assert call_args[1]["data"]["query"] == "SELECT [System.Id] FROM WorkItems"
        assert result == [{"id": 1}, {"id": 2}]

    @patch("cli_anything.azdo.core.wiql.api_post")
    def test_run_wiql_with_top(self, mock_post):
        mock_post.return_value = {"workItems": []}
        run_wiql("SELECT [System.Id] FROM WorkItems", project="Technology", top=10)
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["params"]["$top"] == 10

    @patch("cli_anything.azdo.core.wiql.api_post")
    def test_run_wiql_empty(self, mock_post):
        mock_post.return_value = {"workItems": []}
        result = run_wiql("SELECT [System.Id] FROM WorkItems", project="Technology")
        assert result == []


class TestGetMyWorkitems:

    @patch("cli_anything.azdo.core.wiql.run_wiql")
    @patch("cli_anything.azdo.core.wiql.get_project")
    def test_get_my_workitems_uses_correct_query(self, mock_project, mock_run):
        mock_project.return_value = "Technology"
        mock_run.return_value = [{"id": 42}]
        result = get_my_workitems()
        call_args = mock_run.call_args
        query = call_args[0][0]
        assert "@Me" in query
        assert "Active" in query
        assert result == [{"id": 42}]
