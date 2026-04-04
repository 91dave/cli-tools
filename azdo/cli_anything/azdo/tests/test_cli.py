"""Tests for CLI entry point — command groups, output modes, and invocation."""

import json
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from cli_anything.azdo.azdo_cli import cli


class TestCliInvocation:
    """Test CLI command invocation via Click's CliRunner."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_help_shows_all_groups(self):
        """Top-level --help lists all command groups."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for group in ("auth", "workitem", "comment", "query"):
            assert group in result.output

    @patch("cli_anything.azdo.core.auth.get_auth_status")
    def test_json_flag_sets_output_mode(self, mock_auth):
        """--json flag causes JSON output."""
        mock_auth.return_value = {
            "configured": True,
            "authenticated": True,
            "organization": "TestOrg",
            "project": "TestProject",
        }
        result = self.runner.invoke(cli, ["--json", "auth", "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["authenticated"] is True

    @patch("cli_anything.azdo.core.auth.get_auth_status")
    def test_auth_status_command(self, mock_auth):
        """auth status prints human-readable output."""
        mock_auth.return_value = {
            "configured": True,
            "authenticated": True,
            "organization": "AMDigitalTech",
            "project": "Technology",
        }
        result = self.runner.invoke(cli, ["auth", "status"])
        assert result.exit_code == 0
        assert "authenticated" in result.output.lower() or "AMDigitalTech" in result.output

    @patch("cli_anything.azdo.core.auth.set_defaults")
    def test_auth_set_defaults_command(self, mock_set):
        """auth set-defaults saves configuration."""
        mock_set.return_value = {
            "status": "updated",
            "organization": "AMDigitalTech",
            "project": "Technology",
            "tenant": "adammatthewdigital.onmicrosoft.com",
        }
        result = self.runner.invoke(cli, [
            "auth", "set-defaults",
            "--org", "AMDigitalTech",
            "--project", "Technology",
            "--tenant", "adammatthewdigital.onmicrosoft.com",
        ])
        assert result.exit_code == 0
        mock_set.assert_called_once_with("AMDigitalTech", "Technology", "adammatthewdigital.onmicrosoft.com")

    @patch("cli_anything.azdo.core.workitems.get_workitem")
    def test_workitem_show_command(self, mock_get):
        """workitem show fetches and displays a work item."""
        mock_get.return_value = {
            "id": 12345,
            "title": "Test Item",
            "state": "Active",
            "type": "User Story",
        }
        result = self.runner.invoke(cli, ["workitem", "show", "12345"])
        assert result.exit_code == 0
        assert "12345" in result.output
        mock_get.assert_called_once_with(12345, extra_fields=None)

    @patch("cli_anything.azdo.core.workitems.get_workitem")
    def test_workitem_show_with_field_option(self, mock_get):
        """workitem show --field passes extra_fields through."""
        mock_get.return_value = {
            "id": 12345,
            "title": "Test Item",
            "Custom.MyField": "custom value",
        }
        result = self.runner.invoke(cli, [
            "--json", "workitem", "show", "12345",
            "--field", "Custom.MyField",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["Custom.MyField"] == "custom value"
        mock_get.assert_called_once_with(12345, extra_fields=("Custom.MyField",))

    @patch("cli_anything.azdo.core.workitems.get_workitem_fields")
    def test_workitem_fields_command(self, mock_fields):
        """workitem fields returns all raw fields."""
        mock_fields.return_value = {
            "id": 12345,
            "fields": {
                "Custom.MyField": "val",
                "System.Title": "Test",
            },
        }
        result = self.runner.invoke(cli, ["--json", "workitem", "fields", "12345"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["fields"]["Custom.MyField"] == "val"
        mock_fields.assert_called_once_with(12345, field_names=None)

    @patch("cli_anything.azdo.core.workitems.get_workitem_fields")
    def test_workitem_fields_with_name_filter(self, mock_fields):
        """workitem fields --name filters to specific fields."""
        mock_fields.return_value = {
            "id": 12345,
            "fields": {"Custom.MyField": "val"},
        }
        result = self.runner.invoke(cli, [
            "--json", "workitem", "fields", "12345",
            "--name", "Custom.MyField",
        ])
        assert result.exit_code == 0
        mock_fields.assert_called_once_with(12345, field_names=("Custom.MyField",))

    @patch("cli_anything.azdo.core.comments.list_comments")
    def test_comment_list_command(self, mock_list):
        """comment list displays comments."""
        mock_list.return_value = {
            "count": 1,
            "comments": [{
                "id": 1,
                "author": "Dave Arthur",
                "author_email": "dave@test.com",
                "date": "2026-01-01T12:00:00Z",
                "text": "<p>Hello</p>",
                "text_plain": "Hello",
            }],
        }
        result = self.runner.invoke(cli, ["comment", "list", "12345"])
        assert result.exit_code == 0
        assert "Dave Arthur" in result.output
        mock_list.assert_called_once_with(12345)

    @patch("cli_anything.azdo.core.wiql.get_my_workitems")
    def test_query_mine_command(self, mock_mine):
        """query mine lists current user's active items."""
        mock_mine.return_value = [
            {"id": 100, "url": "https://dev.azure.com/test/_apis/wit/workItems/100"},
            {"id": 200, "url": "https://dev.azure.com/test/_apis/wit/workItems/200"},
        ]
        result = self.runner.invoke(cli, ["query", "mine"])
        assert result.exit_code == 0
        assert "2" in result.output  # "2 work item(s)"
        mock_mine.assert_called_once()

    def test_workitem_fields_shows_in_help(self):
        """workitem subcommand help lists 'fields' command."""
        result = self.runner.invoke(cli, ["workitem", "--help"])
        assert result.exit_code == 0
        assert "fields" in result.output
