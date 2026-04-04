"""Integration tests for cli-anything-azdo.

These tests hit the real Azure DevOps API and require:
  - A valid `az` session against adammatthewdigital.onmicrosoft.com
  - Network access to dev.azure.com

Run with:  pytest -m integration
Skip with: pytest -m "not integration"  (default)
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def skip_if_no_auth():
    """Skip integration tests if az CLI auth is not available.

    Ensures config exists (org/project/tenant) so the backend can resolve
    them.  If the config file is missing, we write defaults before checking.
    """
    try:
        from cli_anything.azdo.utils.azdo_backend import load_config, save_config

        config = load_config()
        if not config.get("organization"):
            save_config({
                "organization": "AMDigitalTech",
                "project": "Technology",
                "tenant": "adammatthewdigital.onmicrosoft.com",
            })

        from cli_anything.azdo.core.auth import get_auth_status

        status = get_auth_status()
        if not status.get("authenticated"):
            pytest.skip("Not authenticated to Azure DevOps")
    except pytest.skip.Exception:
        raise
    except Exception as exc:
        pytest.skip(f"Azure DevOps auth not available: {exc}")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestIntegrationAuth:
    def test_auth_status_reports_authenticated(self):
        from cli_anything.azdo.core.auth import get_auth_status

        status = get_auth_status()
        assert status["authenticated"] is True
        assert status.get("project"), "project name should be present"


# ---------------------------------------------------------------------------
# Work Items
# ---------------------------------------------------------------------------


class TestIntegrationWorkitem:
    def test_get_known_workitem(self):
        from cli_anything.azdo.core.workitems import get_workitem

        item = get_workitem(12345)
        assert item["id"] == 12345
        assert isinstance(item["title"], str) and len(item["title"]) > 0
        assert item["state"] == "Done"

    def test_list_workitems_by_state(self):
        from cli_anything.azdo.core.workitems import list_workitems

        items = list_workitems(state="Done", top=5)
        assert len(items) >= 1
        for item in items:
            assert item["state"] == "Done"

    def test_get_children(self):
        from cli_anything.azdo.core.workitems import get_children

        # 12345 may or may not have children — just verify it returns a list
        children = get_children(12345)
        assert isinstance(children, list)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class TestIntegrationComments:
    def test_list_comments_on_known_item(self):
        from cli_anything.azdo.core.comments import list_comments

        result = list_comments(12345)
        assert result["count"] >= 3, f"Expected >=3 comments, got {result['count']}"
        assert len(result["comments"]) >= 3


# ---------------------------------------------------------------------------
# WIQL
# ---------------------------------------------------------------------------


class TestIntegrationWiql:
    def test_run_raw_wiql(self):
        from cli_anything.azdo.core.wiql import run_wiql

        items = run_wiql(
            "SELECT [System.Id] FROM WorkItems WHERE [System.Id] = 12345"
        )
        assert isinstance(items, list)
        ids = [wi["id"] for wi in items]
        assert 12345 in ids
