"""End-to-end tests for cli-anything-icepanel.

These tests make REAL API calls to IcePanel. They require:
- ICEPANEL_API_KEY env var set with a valid key
- Network access to https://api.icepanel.io

Skip all E2E tests if ICEPANEL_API_KEY is not set.

CLI subprocess tests use _resolve_cli() per HARNESS.md convention.
"""

import json
import os
import subprocess
import sys

import pytest


# Skip entire module if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("ICEPANEL_API_KEY"),
    reason="ICEPANEL_API_KEY not set — skipping E2E tests",
)


def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev."""
    import shutil
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_anything.icepanel.icepanel_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


class TestAuthE2E:
    """Test authentication against the real API."""

    def test_auth_status_authenticated(self):
        """Verify the API key works by checking auth status."""
        from cli_anything.icepanel.core.auth import get_auth_status

        result = get_auth_status()
        assert result["configured"] is True
        assert result["authenticated"] is True
        assert result["organizations_count"] >= 1
        print(f"\n  Authenticated: {result['organizations_count']} organizations")


class TestOrgDiscoveryE2E:
    """Test organization and landscape discovery."""

    def test_list_organizations(self):
        from cli_anything.icepanel.core.organizations import list_organizations

        result = list_organizations()
        assert result["count"] >= 1
        org = result["organizations"][0]
        assert "id" in org
        assert "name" in org
        print(f"\n  First org: {org['name']} ({org['id']})")

    def test_list_landscapes(self):
        from cli_anything.icepanel.core.organizations import (
            list_organizations,
            list_landscapes,
        )

        orgs = list_organizations()
        org_id = orgs["organizations"][0]["id"]
        result = list_landscapes(org_id)
        assert result["count"] >= 0
        print(f"\n  Landscapes in {org_id}: {result['count']}")
        for ls in result["landscapes"][:5]:
            print(f"    - {ls['name']} ({ls['id']})")


class TestModelObjectsE2E:
    """Test model object operations (read-only to avoid modifying real data)."""

    def _get_first_landscape(self):
        from cli_anything.icepanel.core.organizations import (
            list_organizations,
            list_landscapes,
        )
        orgs = list_organizations()
        org_id = orgs["organizations"][0]["id"]
        landscapes = list_landscapes(org_id)
        if landscapes["count"] == 0:
            pytest.skip("No landscapes available for testing")
        return landscapes["landscapes"][0]["id"]

    def test_list_objects(self):
        from cli_anything.icepanel.core.model_objects import list_objects

        lid = self._get_first_landscape()
        result = list_objects(lid, "latest")
        assert "count" in result
        assert "model_objects" in result
        print(f"\n  Objects in {lid}: {result['count']}")
        for obj in result["model_objects"][:5]:
            print(f"    - [{obj['type']}] {obj['name']} ({obj['id']})")

    def test_list_connections(self):
        from cli_anything.icepanel.core.connections import list_connections

        lid = self._get_first_landscape()
        result = list_connections(lid, "latest")
        assert "count" in result
        print(f"\n  Connections: {result['count']}")


class TestFlowsE2E:
    """Test flow operations."""

    def _get_first_landscape(self):
        from cli_anything.icepanel.core.organizations import (
            list_organizations,
            list_landscapes,
        )
        orgs = list_organizations()
        org_id = orgs["organizations"][0]["id"]
        landscapes = list_landscapes(org_id)
        if landscapes["count"] == 0:
            pytest.skip("No landscapes available")
        return landscapes["landscapes"][0]["id"]

    def test_list_flows(self):
        from cli_anything.icepanel.core.flows import list_flows

        lid = self._get_first_landscape()
        result = list_flows(lid, "latest")
        assert "count" in result
        print(f"\n  Flows: {result['count']}")

    def test_export_mermaid(self):
        from cli_anything.icepanel.core.flows import list_flows, export_mermaid

        lid = self._get_first_landscape()
        flows = list_flows(lid, "latest")
        if flows["count"] == 0:
            pytest.skip("No flows to export")
        flow_id = flows["flows"][0]["id"]
        result = export_mermaid(flow_id, lid, "latest")
        assert result is not None
        print(f"\n  Mermaid export for {flow_id}: {str(result)[:200]}")


class TestCLISubprocess:
    """Test the installed CLI command via subprocess."""

    CLI_BASE = _resolve_cli("cli-anything-icepanel")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "IcePanel CLI" in result.stdout

    def test_json_org_list(self):
        result = self._run(["--json", "org", "list"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "count" in data
        assert "organizations" in data
        print(f"\n  CLI org list: {data['count']} organizations")

    def test_json_auth_status(self):
        result = self._run(["--json", "auth", "status"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["authenticated"] is True
