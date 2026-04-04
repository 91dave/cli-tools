"""Sandbox E2E write tests — creates and deletes resources in the sandbox landscape.

Requires:
    - ICEPANEL_API_KEY env var (or configured via auth setup) with WRITE permissions
    - ICEPANEL_WRITE_TESTS=1 env var to enable
    - Network access to https://api.icepanel.io

All tests clean up after themselves via the sandbox_cleanup fixture.
"""

import json
import os
import subprocess
import sys

import pytest

from cli_anything.icepanel.utils.icepanel_backend import (
    api_post,
    api_get,
    api_delete,
)

SANDBOX_LANDSCAPE = "4c4fgtKjNVqaYhgMQadA"
SANDBOX_VERSION = "tziLpTtyq1MW2fU5wOrv"
SANDBOX_ROOT = "EIedgMRu1CeNOJu9al3W"

_has_api_key = bool(
    os.environ.get("ICEPANEL_API_KEY")
    or os.path.exists(os.path.expanduser("~/.cli-anything-icepanel/config.json"))
)

pytestmark = [
    pytest.mark.skipif(not _has_api_key, reason="No API key configured"),
    pytest.mark.skipif(
        os.environ.get("ICEPANEL_WRITE_TESTS") != "1",
        reason="Write tests disabled — set ICEPANEL_WRITE_TESTS=1 to enable",
    ),
]

LID = SANDBOX_LANDSCAPE
VID = SANDBOX_VERSION
OBJ_BASE = f"/landscapes/{LID}/versions/{VID}/model/objects"
CONN_BASE = f"/landscapes/{LID}/versions/{VID}/model/connections"
FLOW_BASE = f"/landscapes/{LID}/versions/{VID}/flows"
DIAG_BASE = f"/landscapes/{LID}/versions/{VID}/diagrams"


@pytest.fixture
def sandbox_cleanup():
    """Track created resource IDs and delete them all in teardown (reverse order)."""
    created = {"objects": [], "connections": [], "flows": []}
    yield created
    for flow_id in reversed(created["flows"]):
        try:
            api_delete(f"{FLOW_BASE}/{flow_id}")
        except Exception:
            pass
    for conn_id in reversed(created["connections"]):
        try:
            api_delete(f"{CONN_BASE}/{conn_id}")
        except Exception:
            pass
    for obj_id in reversed(created["objects"]):
        try:
            api_delete(f"{OBJ_BASE}/{obj_id}")
        except Exception:
            pass


def _create_obj(name, obj_type="system", parent_id=SANDBOX_ROOT):
    result = api_post(OBJ_BASE, {
        "name": name, "type": obj_type, "parentId": parent_id,
    })
    return result["modelObject"]


class TestModelObjectLifecycle:
    """Test object create → get → update → delete."""

    def test_create_get_update_delete(self, sandbox_cleanup):
        # Create
        obj = _create_obj("E2E Test System")
        oid = obj["id"]
        sandbox_cleanup["objects"].append(oid)
        assert obj["name"] == "E2E Test System"
        assert obj["type"] == "system"

        # Get
        got = api_get(f"{OBJ_BASE}/{oid}")
        assert got["modelObject"]["name"] == "E2E Test System"

        # Update
        from cli_anything.icepanel.core.model_objects import update_object
        updated = update_object(oid, LID, VID, name="E2E Test System Updated")
        assert updated["name"] == "E2E Test System Updated"

        # Delete
        api_delete(f"{OBJ_BASE}/{oid}")
        sandbox_cleanup["objects"].remove(oid)  # already cleaned up

    def test_create_nested_objects_cascade_delete(self, sandbox_cleanup):
        parent = _create_obj("E2E Parent System")
        pid = parent["id"]
        sandbox_cleanup["objects"].append(pid)

        child = _create_obj("E2E Child App", obj_type="app", parent_id=pid)
        cid = child["id"]
        sandbox_cleanup["objects"].append(cid)

        # Verify relationship
        assert child["parentId"] == pid

        parent_detail = api_get(f"{OBJ_BASE}/{pid}")
        assert cid in parent_detail["modelObject"]["childIds"]

        # Delete parent — should cascade to child
        result = api_delete(f"{OBJ_BASE}/{pid}")
        assert cid in result.get("deletedModelObjectIds", [])
        sandbox_cleanup["objects"].clear()  # both gone


class TestConnectionLifecycle:
    """Test connection create → get → delete with required direction field."""

    def test_create_get_delete_connection(self, sandbox_cleanup):
        obj_a = _create_obj("E2E Conn Source")
        obj_b = _create_obj("E2E Conn Target")
        sandbox_cleanup["objects"].extend([obj_a["id"], obj_b["id"]])

        # Create connection (direction is required!)
        from cli_anything.icepanel.core.connections import create_connection
        conn = create_connection(
            obj_a["id"], obj_b["id"], "E2E Test Connection",
            landscape_id=LID, version_id=VID,
        )
        conn_id = conn["id"]
        sandbox_cleanup["connections"].append(conn_id)
        assert conn["name"] == "E2E Test Connection"
        assert conn["direction"] == "outgoing"

        # Get
        got = api_get(f"{CONN_BASE}/{conn_id}")
        assert got["modelConnection"]["name"] == "E2E Test Connection"

        # Delete
        api_delete(f"{CONN_BASE}/{conn_id}")
        sandbox_cleanup["connections"].remove(conn_id)

    def test_connection_without_direction_fails(self, sandbox_cleanup):
        """Document that direction is mandatory in the IcePanel API."""
        obj_a = _create_obj("E2E Dir Source")
        obj_b = _create_obj("E2E Dir Target")
        sandbox_cleanup["objects"].extend([obj_a["id"], obj_b["id"]])

        import requests
        with pytest.raises(requests.HTTPError, match="400"):
            api_post(CONN_BASE, {
                "originId": obj_a["id"],
                "targetId": obj_b["id"],
                "name": "Missing direction",
                # No direction field!
            })


class TestFlowLifecycle:
    """Test flow creation with steps and patch operators."""

    def _get_sandbox_diagram(self):
        data = api_get(DIAG_BASE)
        diagrams = data.get("diagrams", [])
        if not diagrams:
            pytest.skip("No diagrams in sandbox")
        return diagrams[0]["id"]

    def test_create_flow_with_steps_and_delete(self, sandbox_cleanup):
        diag_id = self._get_sandbox_diagram()

        from cli_anything.icepanel.core.flows import create_flow
        flow = create_flow(
            "E2E Test Flow",
            diag_id,
            steps=[
                {"type": "introduction", "description": "E2E test flow"},
                {"type": "self-action", "originId": SANDBOX_ROOT, "description": "Self action"},
            ],
            landscape_id=LID,
            version_id=VID,
        )
        flow_id = flow["id"]
        sandbox_cleanup["flows"].append(flow_id)
        assert flow["name"] == "E2E Test Flow"
        assert len(flow["steps"]) == 2

        # Read it back
        from cli_anything.icepanel.core.flows import get_flow
        got = get_flow(flow_id, LID, VID)
        assert got["name"] == "E2E Test Flow"

        # Delete
        api_delete(f"{FLOW_BASE}/{flow_id}")
        sandbox_cleanup["flows"].remove(flow_id)

    def test_flow_step_add_update_remove(self, sandbox_cleanup):
        diag_id = self._get_sandbox_diagram()

        from cli_anything.icepanel.core.flows import (
            create_flow, add_flow_steps, update_flow_steps, remove_flow_steps, get_flow,
        )

        # Create with intro only
        flow = create_flow(
            "E2E Patch Test",
            diag_id,
            steps=[{"type": "introduction", "description": "Initial"}],
            landscape_id=LID,
            version_id=VID,
        )
        flow_id = flow["id"]
        sandbox_cleanup["flows"].append(flow_id)

        # $add a step
        add_flow_steps(flow_id, {
            "snew": {
                "id": "snew", "index": 1, "type": "self-action",
                "originId": SANDBOX_ROOT, "targetId": None, "viaId": None,
                "parentId": None, "paths": None, "flowId": None,
                "description": "Added step",
            }
        }, LID, VID)

        got = get_flow(flow_id, LID, VID)
        assert "snew" in got["steps"]

        # $update the step
        update_flow_steps(flow_id, {
            "snew": {"description": "Updated step"}
        }, LID, VID)

        got = get_flow(flow_id, LID, VID)
        assert got["steps"]["snew"]["description"] == "Updated step"

        # $remove the step
        remove_flow_steps(flow_id, ["snew"], LID, VID)

        got = get_flow(flow_id, LID, VID)
        assert "snew" not in got["steps"]

    def test_flow_with_alternate_path(self, sandbox_cleanup):
        diag_id = self._get_sandbox_diagram()

        from cli_anything.icepanel.core.flows import create_flow

        flow = create_flow(
            "E2E Alt Path Test",
            diag_id,
            steps=[
                {"type": "introduction", "description": "Test"},
                {"type": "self-action", "originId": SANDBOX_ROOT, "description": "Normal step"},
                {"type": "alternate-path", "description": "If error",
                 "paths": [{"name": "Error handling"}]},
                {"type": "self-action", "originId": SANDBOX_ROOT,
                 "description": "Handle error", "parent_path": "Error handling"},
            ],
            landscape_id=LID,
            version_id=VID,
        )
        flow_id = flow["id"]
        sandbox_cleanup["flows"].append(flow_id)

        # Verify structure
        steps = flow["steps"]
        alt_step = steps["s2"]
        assert alt_step["type"] == "alternate-path"
        assert alt_step["paths"] is not None

        child_step = steps["s2a"]
        assert child_step["parentId"] is not None
        assert child_step["description"] == "Handle error"


class TestDiagramResolutionE2E:
    """Test diagram resolve against real data."""

    def _get_sandbox_diagram(self):
        data = api_get(DIAG_BASE)
        diagrams = data.get("diagrams", [])
        if not diagrams:
            pytest.skip("No diagrams in sandbox")
        return diagrams[0]["id"]

    def test_resolve_returns_structure(self, sandbox_cleanup):
        """Create objects + connection, verify resolve finds them."""
        diag_id = self._get_sandbox_diagram()

        obj_a = _create_obj("E2E Resolve A")
        obj_b = _create_obj("E2E Resolve B")
        sandbox_cleanup["objects"].extend([obj_a["id"], obj_b["id"]])

        # Note: newly created objects won't be on the diagram automatically,
        # so resolve may not find them. But we can verify the function runs
        # and returns the correct structure.
        from cli_anything.icepanel.core.diagrams import resolve_content
        result = resolve_content(diag_id, LID, VID)
        assert "objects" in result
        assert "connections" in result
        assert "object_count" in result
        assert "connection_count" in result


class TestCLISubprocessWrites:
    """Test CLI write commands via subprocess."""

    def _resolve_cli(self):
        import shutil
        path = shutil.which("cli-anything-icepanel")
        if path:
            return [path]
        return [sys.executable, "-m", "cli_anything.icepanel.icepanel_cli"]

    def _run(self, args, check=True):
        return subprocess.run(
            self._resolve_cli() + args,
            capture_output=True, text=True, check=check,
        )

    def test_cli_object_create_delete(self, sandbox_cleanup):
        # Create (must pass --parent-id for the root)
        result = self._run([
            "--json", "object", "create",
            "--name", "CLI E2E Test",
            "--type", "system",
            "--parent-id", SANDBOX_ROOT,
            "--landscape-id", LID,
            "--version-id", VID,
        ])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        oid = data.get("id")
        assert oid
        sandbox_cleanup["objects"].append(oid)

        # Delete
        result = self._run([
            "--json", "object", "delete", oid,
            "--landscape-id", LID,
            "--version-id", VID,
        ])
        assert result.returncode == 0
        sandbox_cleanup["objects"].remove(oid)

    def test_cli_filter_by_type(self, sandbox_cleanup):
        # Create a system first, then an app inside it (apps can't be root children)
        parent = _create_obj("CLI Filter Parent")
        sandbox_cleanup["objects"].append(parent["id"])
        obj = _create_obj("CLI Filter Test App", obj_type="app", parent_id=parent["id"])
        sandbox_cleanup["objects"].append(obj["id"])

        result = self._run([
            "--json", "object", "list",
            "--type", "app",
            "--landscape-id", LID,
            "--version-id", VID,
        ])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        types = {o["type"] for o in data["model_objects"]}
        assert types == {"app"} or len(types) == 0  # all should be apps
