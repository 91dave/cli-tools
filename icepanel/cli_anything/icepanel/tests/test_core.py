"""Unit tests for cli-anything-icepanel — synthetic data, no network calls.

Tests core module logic: formatting, validation, body construction,
config management, and default resolution.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ── Backend Tests ────────────────────────────────────────────────

class TestBackendConfig:
    """Test config save/load and API key resolution."""

    def test_save_load_roundtrip(self, tmp_path):
        """Config save → load produces identical data."""
        from cli_anything.icepanel.utils import icepanel_backend as be

        config_file = tmp_path / "config.json"
        with patch.object(be, "CONFIG_FILE", config_file), \
             patch.object(be, "CONFIG_DIR", tmp_path):
            be.save_config({"api_key": "test:secret", "organization_id": "org123"})
            loaded = be.load_config()
            assert loaded["api_key"] == "test:secret"
            assert loaded["organization_id"] == "org123"

    def test_load_config_missing_file(self, tmp_path):
        """load_config returns {} when file doesn't exist."""
        from cli_anything.icepanel.utils import icepanel_backend as be

        with patch.object(be, "CONFIG_FILE", tmp_path / "nonexistent.json"):
            assert be.load_config() == {}

    def test_get_api_key_from_env(self):
        """Env var ICEPANEL_API_KEY takes priority."""
        from cli_anything.icepanel.utils import icepanel_backend as be

        with patch.dict(os.environ, {"ICEPANEL_API_KEY": "env:key"}):
            assert be._get_api_key() == "env:key"

    def test_get_api_key_from_config(self, tmp_path):
        """Falls back to config file when no env var."""
        from cli_anything.icepanel.utils import icepanel_backend as be

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"api_key": "file:key"}))
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(be, "CONFIG_FILE", config_file):
            # Remove env var if present
            os.environ.pop("ICEPANEL_API_KEY", None)
            assert be._get_api_key() == "file:key"

    def test_get_api_key_missing_raises(self, tmp_path):
        """RuntimeError when no key in env or config."""
        from cli_anything.icepanel.utils import icepanel_backend as be

        with patch.dict(os.environ, {}, clear=True), \
             patch.object(be, "CONFIG_FILE", tmp_path / "empty.json"):
            os.environ.pop("ICEPANEL_API_KEY", None)
            with pytest.raises(RuntimeError, match="Not authenticated"):
                be._get_api_key()

    def test_get_default_org_id_from_env(self):
        """Env var takes priority for org ID."""
        from cli_anything.icepanel.utils import icepanel_backend as be

        with patch.dict(os.environ, {"ICEPANEL_ORG_ID": "envorg"}):
            assert be._get_default_org_id() == "envorg"

    def test_get_default_version_id_fallback(self, tmp_path):
        """Version ID defaults to 'latest'."""
        from cli_anything.icepanel.utils import icepanel_backend as be

        with patch.dict(os.environ, {}, clear=True), \
             patch.object(be, "CONFIG_FILE", tmp_path / "empty.json"):
            os.environ.pop("ICEPANEL_VERSION_ID", None)
            assert be._get_default_version_id() == "latest"

    def test_config_file_permissions(self, tmp_path):
        """Config file should be 0o600 (owner-only)."""
        from cli_anything.icepanel.utils import icepanel_backend as be

        config_file = tmp_path / "config.json"
        with patch.object(be, "CONFIG_FILE", config_file), \
             patch.object(be, "CONFIG_DIR", tmp_path):
            be.save_config({"api_key": "test:key"})
            # Check file exists and is readable
            assert config_file.exists()
            stat = config_file.stat()
            assert stat.st_mode & 0o777 == 0o600


# ── Auth Tests ───────────────────────────────────────────────────

class TestAuth:
    """Test auth core module."""

    def test_setup_stores_key(self, tmp_path):
        from cli_anything.icepanel.core import auth as auth_mod
        from cli_anything.icepanel.utils import icepanel_backend as be

        config_file = tmp_path / "config.json"
        with patch.object(be, "CONFIG_FILE", config_file), \
             patch.object(be, "CONFIG_DIR", tmp_path):
            result = auth_mod.setup_api_key("k:s", organization_id="org1")
            assert result["status"] == "configured"
            assert result["organization_id"] == "org1"
            loaded = json.loads(config_file.read_text())
            assert loaded["api_key"] == "k:s"

    def test_set_defaults_requires_key(self, tmp_path):
        from cli_anything.icepanel.core import auth as auth_mod
        from cli_anything.icepanel.utils import icepanel_backend as be

        with patch.object(be, "CONFIG_FILE", tmp_path / "empty.json"), \
             patch.object(be, "CONFIG_DIR", tmp_path):
            with pytest.raises(RuntimeError, match="Not authenticated"):
                auth_mod.set_defaults(organization_id="org1")

    def test_logout_removes_file(self, tmp_path):
        from cli_anything.icepanel.core import auth as auth_mod
        from cli_anything.icepanel.utils import icepanel_backend as be

        config_file = tmp_path / "config.json"
        config_file.write_text("{}")
        with patch.object(be, "CONFIG_DIR", tmp_path), \
             patch.object(be, "CONFIG_FILE", config_file), \
             patch.object(auth_mod, "CONFIG_DIR", tmp_path):
            result = auth_mod.logout()
            assert result["status"] == "logged_out"
            assert not config_file.exists()

    def test_get_auth_status_unconfigured(self, tmp_path):
        from cli_anything.icepanel.core import auth as auth_mod
        from cli_anything.icepanel.utils import icepanel_backend as be

        with patch.object(be, "CONFIG_FILE", tmp_path / "empty.json"), \
             patch.object(be, "CONFIG_DIR", tmp_path):
            result = auth_mod.get_auth_status()
            assert result["configured"] is False
            assert result["authenticated"] is False


# ── Organization Tests ───────────────────────────────────────────

class TestOrganizations:
    """Test organization core module."""

    def test_require_org_id_from_arg(self):
        from cli_anything.icepanel.core.organizations import _require_org_id
        assert _require_org_id("abc") == "abc"

    def test_require_org_id_missing_raises(self):
        from cli_anything.icepanel.core.organizations import _require_org_id
        with patch("cli_anything.icepanel.core.organizations._get_default_org_id", return_value=None):
            with pytest.raises(RuntimeError, match="Organization ID required"):
                _require_org_id(None)

    @patch("cli_anything.icepanel.core.organizations.api_get")
    def test_list_organizations(self, mock_get):
        from cli_anything.icepanel.core.organizations import list_organizations
        mock_get.return_value = {"organizations": [
            {"id": "o1", "name": "Acme", "plan": "growth", "status": "active",
             "seats": 5, "userIds": ["u1", "u2"], "createdAt": "2025-01-01"},
        ]}
        result = list_organizations()
        assert result["count"] == 1
        assert result["organizations"][0]["name"] == "Acme"
        assert result["organizations"][0]["user_count"] == 2

    @patch("cli_anything.icepanel.core.organizations.api_post")
    def test_create_landscape(self, mock_post):
        from cli_anything.icepanel.core.organizations import create_landscape
        mock_post.return_value = {
            "landscape": {"id": "l1", "name": "Prod"},
            "version": {"id": "v1"},
        }
        with patch("cli_anything.icepanel.core.organizations._require_org_id", return_value="org1"):
            result = create_landscape("Prod")
            mock_post.assert_called_once_with("/organizations/org1/landscapes", {"name": "Prod"})


# ── Model Objects Tests ──────────────────────────────────────────

class TestModelObjects:
    """Test model object core module."""

    @patch("cli_anything.icepanel.core.model_objects.api_get")
    def test_list_objects(self, mock_get):
        from cli_anything.icepanel.core.model_objects import list_objects
        mock_get.return_value = {"modelObjects": [
            {"id": "m1", "name": "API Gateway", "type": "app", "status": "active",
             "parentId": None, "parentIds": [], "childIds": [], "caption": "",
             "description": "", "external": False, "domainId": "", "tagIds": [],
             "technologyIds": [], "teamIds": [], "labels": {},
             "createdAt": "", "updatedAt": ""},
        ]}
        with patch("cli_anything.icepanel.core.model_objects._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.model_objects._get_default_version_id", return_value="latest"):
            result = list_objects()
            assert result["count"] == 1
            assert result["model_objects"][0]["name"] == "API Gateway"

    @patch("cli_anything.icepanel.core.model_objects.api_post")
    def test_create_object_body(self, mock_post):
        from cli_anything.icepanel.core.model_objects import create_object
        mock_post.return_value = {"modelObject": {"id": "new1"}}
        with patch("cli_anything.icepanel.core.model_objects._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.model_objects._get_default_version_id", return_value="latest"):
            create_object("MyApp", "app", parent_id="sys1", description="Test app")
            call_args = mock_post.call_args
            body = call_args[0][1]
            assert body["name"] == "MyApp"
            assert body["type"] == "app"
            assert body["parentId"] == "sys1"
            assert body["description"] == "Test app"

    def test_update_object_empty_raises(self):
        from cli_anything.icepanel.core.model_objects import update_object
        with patch("cli_anything.icepanel.core.model_objects._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.model_objects._get_default_version_id", return_value="latest"):
            with pytest.raises(ValueError, match="No fields"):
                update_object("obj1")

    def test_lv_missing_landscape_raises(self):
        from cli_anything.icepanel.core.model_objects import _lv
        with patch("cli_anything.icepanel.core.model_objects._get_default_landscape_id", return_value=None):
            with pytest.raises(RuntimeError, match="Landscape ID required"):
                _lv(None, None)


# ── Connections Tests ────────────────────────────────────────────

class TestConnections:
    """Test connections core module."""

    @patch("cli_anything.icepanel.core.connections.api_post")
    def test_create_connection_body(self, mock_post):
        from cli_anything.icepanel.core.connections import create_connection
        mock_post.return_value = {"modelConnection": {"id": "c1"}}
        with patch("cli_anything.icepanel.core.connections._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.connections._get_default_version_id", return_value="latest"):
            create_connection("obj1", "obj2", "REST API", description="HTTP calls")
            body = mock_post.call_args[0][1]
            assert body["originId"] == "obj1"
            assert body["targetId"] == "obj2"
            assert body["name"] == "REST API"
            assert body["description"] == "HTTP calls"

    def test_update_connection_empty_raises(self):
        from cli_anything.icepanel.core.connections import update_connection
        with patch("cli_anything.icepanel.core.connections._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.connections._get_default_version_id", return_value="latest"):
            with pytest.raises(ValueError, match="No fields"):
                update_connection("c1")


# ── Flows Tests ──────────────────────────────────────────────────

class TestFlows:
    """Test flows core module."""

    @patch("cli_anything.icepanel.core.flows.api_get")
    def test_list_flows(self, mock_get):
        from cli_anything.icepanel.core.flows import list_flows
        mock_get.return_value = {"flows": [
            {"id": "f1", "name": "Checkout", "description": "", "landscapeId": "l1",
             "versionId": "v1", "steps": [], "createdAt": "", "updatedAt": ""},
        ]}
        with patch("cli_anything.icepanel.core.flows._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.flows._get_default_version_id", return_value="latest"):
            result = list_flows()
            assert result["count"] == 1
            assert result["flows"][0]["name"] == "Checkout"

    @patch("cli_anything.icepanel.core.flows.api_get")
    def test_export_mermaid_url(self, mock_get):
        from cli_anything.icepanel.core.flows import export_mermaid
        mock_get.return_value = {"mermaid": "sequenceDiagram ..."}
        with patch("cli_anything.icepanel.core.flows._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.flows._get_default_version_id", return_value="v1"):
            export_mermaid("f1")
            mock_get.assert_called_once_with("/landscapes/l1/versions/v1/flows/f1/export/mermaid")


# ── Diagrams Tests ───────────────────────────────────────────────

class TestDiagrams:
    """Test diagrams core module."""

    @patch("cli_anything.icepanel.core.diagrams.api_get")
    def test_list_diagrams(self, mock_get):
        from cli_anything.icepanel.core.diagrams import list_diagrams
        mock_get.return_value = {"diagrams": []}
        with patch("cli_anything.icepanel.core.diagrams._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.diagrams._get_default_version_id", return_value="latest"):
            result = list_diagrams()
            assert result["count"] == 0

    @patch("cli_anything.icepanel.core.diagrams.api_head")
    def test_exists_diagram(self, mock_head):
        from cli_anything.icepanel.core.diagrams import exists_diagram
        mock_head.return_value = {"status": "success", "status_code": 200}
        with patch("cli_anything.icepanel.core.diagrams._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.diagrams._get_default_version_id", return_value="latest"):
            result = exists_diagram("d1")
            assert result["exists"] is True


# ── Tags Tests ───────────────────────────────────────────────────

class TestTags:
    """Test tags core module."""

    @patch("cli_anything.icepanel.core.tags.api_get")
    def test_list_tags(self, mock_get):
        from cli_anything.icepanel.core.tags import list_tags
        mock_get.return_value = {"tags": [
            {"id": "t1", "name": "deprecated", "color": "red", "groupId": "g1",
             "index": 0, "modelObjectIds": ["o1"], "modelConnectionIds": []},
        ]}
        with patch("cli_anything.icepanel.core.tags._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.tags._get_default_version_id", return_value="latest"):
            result = list_tags()
            assert result["count"] == 1
            assert result["tags"][0]["color"] == "red"

    @patch("cli_anything.icepanel.core.tags.api_post")
    def test_create_tag_body(self, mock_post):
        from cli_anything.icepanel.core.tags import create_tag
        mock_post.return_value = {"tag": {"id": "t2"}}
        with patch("cli_anything.icepanel.core.tags._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.tags._get_default_version_id", return_value="latest"):
            create_tag("critical", "red", "g1", index=0)
            body = mock_post.call_args[0][1]
            assert body["name"] == "critical"
            assert body["color"] == "red"
            assert body["groupId"] == "g1"


# ── Versions Tests ───────────────────────────────────────────────

class TestVersions:
    """Test versions core module."""

    @patch("cli_anything.icepanel.core.versions.api_get")
    def test_list_versions(self, mock_get):
        from cli_anything.icepanel.core.versions import list_versions
        mock_get.return_value = {"versions": [
            {"id": "v1", "name": "v1.0", "notes": "", "landscapeId": "l1",
             "tags": [], "createdAt": "", "updatedAt": ""},
        ]}
        with patch("cli_anything.icepanel.core.versions._get_default_landscape_id", return_value="l1"):
            result = list_versions()
            assert result["count"] == 1
            assert result["versions"][0]["name"] == "v1.0"

    def test_update_version_empty_raises(self):
        from cli_anything.icepanel.core.versions import update_version
        with patch("cli_anything.icepanel.core.versions._get_default_landscape_id", return_value="l1"):
            with pytest.raises(ValueError, match="No fields"):
                update_version("v1")


# ── Diagram Resolution Tests ─────────────────────────────────────

class TestDiagramResolution:
    """Test diagram content resolution and ID lookup."""

    def _mock_resolution_data(self):
        """Build mock data for diagram content, objects, and connections."""
        diagram_content = {
            "diagramContent": {
                "items": {},
                "connections": {
                    "dc1": {
                        "id": "dc1", "modelId": "mc1",
                        "originId": "do1", "targetId": "do2",
                    },
                    "dc2": {
                        "id": "dc2", "modelId": "mc2",
                        "originId": "do2", "targetId": "do3",
                    },
                },
            }
        }
        objects_data = {"modelObjects": [
            {"id": "mo1", "name": "Service A", "type": "app",
             "status": "live", "parentId": None, "parentIds": [], "childIds": [],
             "caption": "", "description": "", "external": False,
             "domainId": "", "tagIds": [], "technologyIds": [], "teamIds": [],
             "labels": {}, "createdAt": "", "updatedAt": ""},
            {"id": "mo2", "name": "Service B", "type": "system",
             "status": "live", "parentId": None, "parentIds": [], "childIds": [],
             "caption": "", "description": "", "external": False,
             "domainId": "", "tagIds": [], "technologyIds": [], "teamIds": [],
             "labels": {}, "createdAt": "", "updatedAt": ""},
            {"id": "mo3", "name": "Database X", "type": "store",
             "status": "live", "parentId": None, "parentIds": [], "childIds": [],
             "caption": "", "description": "", "external": False,
             "domainId": "", "tagIds": [], "technologyIds": [], "teamIds": [],
             "labels": {}, "createdAt": "", "updatedAt": ""},
        ]}
        conns_data = {"modelConnections": [
            {"id": "mc1", "name": "REST API", "originId": "mo1", "targetId": "mo2"},
            {"id": "mc2", "name": "Read data", "originId": "mo2", "targetId": "mo3"},
        ]}
        return diagram_content, objects_data, conns_data

    @patch("cli_anything.icepanel.core.diagrams.api_get")
    def test_resolve_content(self, mock_get):
        from cli_anything.icepanel.core.diagrams import resolve_content
        dc, objs, conns = self._mock_resolution_data()
        mock_get.side_effect = [dc, objs, conns]
        with patch("cli_anything.icepanel.core.diagrams._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.diagrams._get_default_version_id", return_value="latest"):
            result = resolve_content("diag1")
            assert result["object_count"] == 3
            assert result["connection_count"] == 2
            names = {o["name"] for o in result["objects"]}
            assert "Service A" in names
            assert "Service B" in names
            assert "Database X" in names
            conn_names = {c["name"] for c in result["connections"]}
            assert "REST API" in conn_names

    @patch("cli_anything.icepanel.core.diagrams.api_get")
    def test_resolve_content_unmapped_items(self, mock_get):
        from cli_anything.icepanel.core.diagrams import resolve_content
        dc = {"diagramContent": {"items": {}, "connections": {
            "dc1": {"id": "dc1", "modelId": "mc_missing", "originId": "do1", "targetId": "do2"},
        }}}
        mock_get.side_effect = [dc, {"modelObjects": []}, {"modelConnections": []}]
        with patch("cli_anything.icepanel.core.diagrams._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.diagrams._get_default_version_id", return_value="latest"):
            result = resolve_content("diag1")
            assert result["object_count"] == 0
            assert result["connection_count"] == 1
            assert result["connections"][0]["name"] == "unknown"

    @patch("cli_anything.icepanel.core.diagrams.api_get")
    def test_lookup_by_object_name(self, mock_get):
        from cli_anything.icepanel.core.diagrams import lookup_diagram_id
        dc, objs, conns = self._mock_resolution_data()
        mock_get.side_effect = [dc, objs, conns]
        with patch("cli_anything.icepanel.core.diagrams._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.diagrams._get_default_version_id", return_value="latest"):
            result = lookup_diagram_id("diag1", "Service A")
            assert len(result["objects"]) == 1
            assert result["objects"][0]["diagram_id"] == "do1"

    @patch("cli_anything.icepanel.core.diagrams.api_get")
    def test_lookup_by_connection_name(self, mock_get):
        from cli_anything.icepanel.core.diagrams import lookup_diagram_id
        dc, objs, conns = self._mock_resolution_data()
        mock_get.side_effect = [dc, objs, conns]
        with patch("cli_anything.icepanel.core.diagrams._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.diagrams._get_default_version_id", return_value="latest"):
            result = lookup_diagram_id("diag1", "REST")
            assert len(result["connections"]) == 1
            assert result["connections"][0]["diagram_id"] == "dc1"

    @patch("cli_anything.icepanel.core.diagrams.api_get")
    def test_lookup_no_match(self, mock_get):
        from cli_anything.icepanel.core.diagrams import lookup_diagram_id
        dc, objs, conns = self._mock_resolution_data()
        mock_get.side_effect = [dc, objs, conns]
        with patch("cli_anything.icepanel.core.diagrams._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.diagrams._get_default_version_id", return_value="latest"):
            result = lookup_diagram_id("diag1", "nonexistent")
            assert len(result["objects"]) == 0
            assert len(result["connections"]) == 0


# ── Flow Creation Tests ──────────────────────────────────────────

class TestFlowCreation:
    """Test flow creation with steps and patch operators."""

    def test_build_steps_from_list(self):
        from cli_anything.icepanel.core.flows import build_steps_from_list
        step_list = [
            {"type": "introduction", "description": "Overview"},
            {"type": "outgoing", "originId": "o1", "targetId": "t1",
             "viaId": "v1", "description": "Step 1"},
            {"type": "self-action", "originId": "o1", "description": "User action"},
        ]
        steps = build_steps_from_list(step_list)
        assert len(steps) == 3
        assert steps["s0"]["type"] == "introduction"
        assert steps["s0"]["index"] == 0
        assert steps["s1"]["originId"] == "o1"
        assert steps["s1"]["viaId"] == "v1"
        assert steps["s2"]["type"] == "self-action"

    def test_build_steps_alternate_path(self):
        from cli_anything.icepanel.core.flows import build_steps_from_list
        step_list = [
            {"type": "introduction", "description": "Test"},
            {"type": "outgoing", "originId": "o1", "targetId": "t1", "description": "Normal"},
            {"type": "alternate-path", "description": "If error",
             "paths": [{"name": "Error path"}]},
            {"type": "outgoing", "originId": "o1", "targetId": "err",
             "description": "Log error", "parent_path": "Error path"},
        ]
        steps = build_steps_from_list(step_list)
        assert len(steps) == 4
        # The alternate-path step should have paths
        alt_step = steps["s2"]
        assert alt_step["type"] == "alternate-path"
        assert "p1" in alt_step["paths"]
        # The child step should reference the path
        child = steps["s2a"]
        assert child["parentId"] == "p1"
        assert child["originId"] == "o1"

    def test_build_steps_empty_raises(self):
        from cli_anything.icepanel.core.flows import build_steps_from_list
        with pytest.raises(ValueError, match="empty"):
            build_steps_from_list([])

    def test_build_steps_name_resolution(self):
        """Test that origin/target/via name fields are picked up."""
        from cli_anything.icepanel.core.flows import build_steps_from_list
        step_list = [
            {"type": "introduction", "description": "Test"},
            {"type": "outgoing", "origin": "DAM User", "target": "DAM UI",
             "via": "Visits", "description": "Navigate"},
        ]
        steps = build_steps_from_list(step_list)
        assert steps["s1"]["originId"] == "DAM User"
        assert steps["s1"]["targetId"] == "DAM UI"
        assert steps["s1"]["viaId"] == "Visits"

    @patch("cli_anything.icepanel.core.flows.api_post")
    def test_create_flow_with_steps(self, mock_post):
        from cli_anything.icepanel.core.flows import create_flow
        mock_post.return_value = {"flow": {"id": "f1"}}
        with patch("cli_anything.icepanel.core.flows._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.flows._get_default_version_id", return_value="v1"):
            create_flow("Test Flow", "diag1", steps=[
                {"type": "introduction", "description": "Test"},
            ])
            body = mock_post.call_args[0][1]
            assert body["name"] == "Test Flow"
            assert body["diagramId"] == "diag1"
            assert "s0" in body["steps"]

    @patch("cli_anything.icepanel.core.flows.api_patch")
    def test_add_flow_steps_uses_add_operator(self, mock_patch):
        from cli_anything.icepanel.core.flows import add_flow_steps
        mock_patch.return_value = {"flow": {"id": "f1"}}
        with patch("cli_anything.icepanel.core.flows._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.flows._get_default_version_id", return_value="v1"):
            add_flow_steps("f1", {"s99": {"id": "s99", "type": "outgoing"}})
            body = mock_patch.call_args[0][1]
            assert "$add" in body["steps"]
            assert "s99" in body["steps"]["$add"]

    @patch("cli_anything.icepanel.core.flows.api_patch")
    def test_update_flow_steps_uses_update_operator(self, mock_patch):
        from cli_anything.icepanel.core.flows import update_flow_steps
        mock_patch.return_value = {"flow": {"id": "f1"}}
        with patch("cli_anything.icepanel.core.flows._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.flows._get_default_version_id", return_value="v1"):
            update_flow_steps("f1", {"s2": {"viaId": "newconn1"}})
            body = mock_patch.call_args[0][1]
            assert "$update" in body["steps"]
            assert body["steps"]["$update"]["s2"]["viaId"] == "newconn1"

    @patch("cli_anything.icepanel.core.flows.api_patch")
    def test_remove_flow_steps_uses_remove_operator(self, mock_patch):
        from cli_anything.icepanel.core.flows import remove_flow_steps
        mock_patch.return_value = {"flow": {"id": "f1"}}
        with patch("cli_anything.icepanel.core.flows._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.flows._get_default_version_id", return_value="v1"):
            remove_flow_steps("f1", ["s3", "s4"])
            body = mock_patch.call_args[0][1]
            assert "$remove" in body["steps"]
            assert body["steps"]["$remove"] == ["s3", "s4"]


# ── Connection Direction Tests ───────────────────────────────────

class TestConnectionDirection:
    """Test that connection create includes direction."""

    @patch("cli_anything.icepanel.core.connections.api_post")
    def test_create_connection_includes_direction(self, mock_post):
        from cli_anything.icepanel.core.connections import create_connection
        mock_post.return_value = {"modelConnection": {"id": "c1"}}
        with patch("cli_anything.icepanel.core.connections._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.connections._get_default_version_id", return_value="latest"):
            create_connection("obj1", "obj2", "test conn")
            body = mock_post.call_args[0][1]
            assert body["direction"] == "outgoing"

    @patch("cli_anything.icepanel.core.connections.api_post")
    def test_create_connection_custom_direction(self, mock_post):
        from cli_anything.icepanel.core.connections import create_connection
        mock_post.return_value = {"modelConnection": {"id": "c1"}}
        with patch("cli_anything.icepanel.core.connections._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.connections._get_default_version_id", return_value="latest"):
            create_connection("obj1", "obj2", "test", direction="bidirectional")
            body = mock_post.call_args[0][1]
            assert body["direction"] == "bidirectional"


# ── Filter Tests ─────────────────────────────────────────────────

class TestFilters:
    """Test client-side filtering on list commands."""

    @patch("cli_anything.icepanel.core.model_objects.api_get")
    def test_list_objects_filter_by_type(self, mock_get):
        from cli_anything.icepanel.core.model_objects import list_objects
        mock_get.return_value = {"modelObjects": [
            {"id": "1", "name": "A", "type": "app", "status": "", "parentId": None,
             "parentIds": [], "childIds": [], "caption": "", "description": "",
             "external": False, "domainId": "", "tagIds": [], "technologyIds": [],
             "teamIds": [], "labels": {}, "createdAt": "", "updatedAt": ""},
            {"id": "2", "name": "B", "type": "system", "status": "", "parentId": None,
             "parentIds": [], "childIds": [], "caption": "", "description": "",
             "external": False, "domainId": "", "tagIds": [], "technologyIds": [],
             "teamIds": [], "labels": {}, "createdAt": "", "updatedAt": ""},
        ]}
        with patch("cli_anything.icepanel.core.model_objects._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.model_objects._get_default_version_id", return_value="latest"):
            result = list_objects(type_filter="app")
            assert result["count"] == 1
            assert result["model_objects"][0]["name"] == "A"

    @patch("cli_anything.icepanel.core.model_objects.api_get")
    def test_list_objects_filter_by_name(self, mock_get):
        from cli_anything.icepanel.core.model_objects import list_objects
        mock_get.return_value = {"modelObjects": [
            {"id": "1", "name": "API Gateway", "type": "app", "status": "", "parentId": None,
             "parentIds": [], "childIds": [], "caption": "", "description": "",
             "external": False, "domainId": "", "tagIds": [], "technologyIds": [],
             "teamIds": [], "labels": {}, "createdAt": "", "updatedAt": ""},
            {"id": "2", "name": "Database", "type": "store", "status": "", "parentId": None,
             "parentIds": [], "childIds": [], "caption": "", "description": "",
             "external": False, "domainId": "", "tagIds": [], "technologyIds": [],
             "teamIds": [], "labels": {}, "createdAt": "", "updatedAt": ""},
        ]}
        with patch("cli_anything.icepanel.core.model_objects._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.model_objects._get_default_version_id", return_value="latest"):
            result = list_objects(name_filter="gateway")
            assert result["count"] == 1
            assert result["model_objects"][0]["name"] == "API Gateway"

    @patch("cli_anything.icepanel.core.model_objects.api_get")
    def test_list_objects_filter_by_tag(self, mock_get):
        from cli_anything.icepanel.core.model_objects import list_objects
        mock_get.return_value = {"modelObjects": [
            {"id": "1", "name": "A", "type": "app", "status": "", "parentId": None,
             "parentIds": [], "childIds": [], "caption": "", "description": "",
             "external": False, "domainId": "", "tagIds": ["t1"], "technologyIds": [],
             "teamIds": [], "labels": {}, "createdAt": "", "updatedAt": ""},
            {"id": "2", "name": "B", "type": "app", "status": "", "parentId": None,
             "parentIds": [], "childIds": [], "caption": "", "description": "",
             "external": False, "domainId": "", "tagIds": [], "technologyIds": [],
             "teamIds": [], "labels": {}, "createdAt": "", "updatedAt": ""},
        ]}
        with patch("cli_anything.icepanel.core.model_objects._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.model_objects._get_default_version_id", return_value="latest"):
            result = list_objects(tag_id_filter="t1")
            assert result["count"] == 1

    @patch("cli_anything.icepanel.core.connections.api_get")
    def test_list_connections_filter_by_name(self, mock_get):
        from cli_anything.icepanel.core.connections import list_connections
        mock_get.return_value = {"modelConnections": [
            {"id": "c1", "name": "REST API", "originId": "o1", "targetId": "t1",
             "direction": "outgoing", "description": "", "status": "",
             "viaId": None, "tagIds": [], "technologyIds": [],
             "createdAt": "", "updatedAt": ""},
            {"id": "c2", "name": "CRUD", "originId": "o2", "targetId": "t2",
             "direction": "outgoing", "description": "", "status": "",
             "viaId": None, "tagIds": [], "technologyIds": [],
             "createdAt": "", "updatedAt": ""},
        ]}
        with patch("cli_anything.icepanel.core.connections._get_default_landscape_id", return_value="l1"), \
             patch("cli_anything.icepanel.core.connections._get_default_version_id", return_value="latest"):
            result = list_connections(name_filter="rest")
            assert result["count"] == 1
            assert result["model_connections"][0]["name"] == "REST API"


# ── Audit Logs Tests ─────────────────────────────────────────────

class TestAuditLogs:
    """Test landscape action logs."""

    @patch("cli_anything.icepanel.core.landscapes.api_get")
    def test_list_action_logs(self, mock_get):
        from cli_anything.icepanel.core.landscapes import list_action_logs
        mock_get.return_value = {"actionLogs": [
            {"id": "log1", "action": {"type": "model-object-create"},
             "performedBy": "user", "performedById": "u1",
             "performedByName": "Alice", "performedAt": "2026-01-01T00:00:00Z"},
            {"id": "log2", "action": {"type": "diagram-content-view"},
             "performedBy": "api-key", "performedById": "k1",
             "performedByName": "ExportKey", "performedAt": "2026-01-01T01:00:00Z"},
        ]}
        with patch("cli_anything.icepanel.core.landscapes._get_default_landscape_id", return_value="l1"):
            result = list_action_logs()
            assert result["count"] == 2
            assert result["logs"][0]["performed_by_name"] == "Alice"

    @patch("cli_anything.icepanel.core.landscapes.api_get")
    def test_list_action_logs_filter_by_api_key(self, mock_get):
        from cli_anything.icepanel.core.landscapes import list_action_logs
        mock_get.return_value = {"actionLogs": [
            {"id": "log1", "action": {"type": "model-object-create"},
             "performedBy": "user", "performedById": "u1",
             "performedByName": "Alice", "performedAt": ""},
            {"id": "log2", "action": {"type": "diagram-content-view"},
             "performedBy": "api-key", "performedById": "k1",
             "performedByName": "ExportKey", "performedAt": ""},
        ]}
        with patch("cli_anything.icepanel.core.landscapes._get_default_landscape_id", return_value="l1"):
            result = list_action_logs(performed_by="api-key")
            assert result["count"] == 1
            assert result["logs"][0]["performed_by"] == "api-key"


# ── Organizations Extended Tests ─────────────────────────────────

class TestOrganizationsExtended:
    """Test technologies and formatted users."""

    @patch("cli_anything.icepanel.core.organizations.api_get")
    def test_list_technologies(self, mock_get):
        from cli_anything.icepanel.core.organizations import list_technologies
        mock_get.return_value = {"catalogTechnologies": [
            {"id": "t1", "name": ".NET", "nameShort": ".NET", "type": "framework",
             "provider": "Microsoft", "status": "approved", "color": "blue"},
        ]}
        with patch("cli_anything.icepanel.core.organizations._get_default_org_id", return_value="o1"):
            result = list_technologies()
            assert result["count"] == 1
            assert result["technologies"][0]["name"] == ".NET"

    @patch("cli_anything.icepanel.core.organizations.api_get")
    def test_list_users_formatted(self, mock_get):
        from cli_anything.icepanel.core.organizations import list_users
        mock_get.return_value = {"organizationUsers": {
            "u1": {"email": "alice@example.com", "permission": "admin",
                   "name": "Alice", "lastActiveAt": "2026-01-01"},
            "u2": {"email": "bob@example.com", "permission": "editor",
                   "name": "Bob", "lastActiveAt": "2026-01-02"},
        }}
        with patch("cli_anything.icepanel.core.organizations._get_default_org_id", return_value="o1"):
            result = list_users()
            assert result["count"] == 2
            emails = {u["email"] for u in result["users"]}
            assert "alice@example.com" in emails
            perms = {u["permission"] for u in result["users"]}
            assert "admin" in perms


# ── Teams Tests ──────────────────────────────────────────────────

class TestTeams:
    """Test teams core module."""

    @patch("cli_anything.icepanel.core.teams.api_get")
    def test_list_teams(self, mock_get):
        from cli_anything.icepanel.core.teams import list_teams
        mock_get.return_value = {"teams": [
            {"id": "t1", "name": "Platform", "color": "blue", "userIds": ["u1"],
             "modelObjectHandleIds": [], "organizationId": "o1"},
        ]}
        with patch("cli_anything.icepanel.core.teams._get_default_org_id", return_value="o1"):
            result = list_teams()
            assert result["count"] == 1
            assert result["teams"][0]["name"] == "Platform"
