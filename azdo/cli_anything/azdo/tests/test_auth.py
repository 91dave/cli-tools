"""Tests for auth module — set_defaults, get_auth_status."""

import json
from unittest.mock import patch, MagicMock

import pytest

from cli_anything.azdo.core.auth import set_defaults, get_auth_status
from cli_anything.azdo.utils.azdo_backend import save_config, load_config


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Redirect config to a temp directory for every test."""
    config_dir = tmp_path / ".cli-anything-azdo"
    config_file = config_dir / "config.json"
    monkeypatch.setattr("cli_anything.azdo.utils.azdo_backend.CONFIG_DIR", config_dir)
    monkeypatch.setattr("cli_anything.azdo.utils.azdo_backend.CONFIG_FILE", config_file)
    monkeypatch.delenv("AZDO_ORG", raising=False)
    monkeypatch.delenv("AZDO_PROJECT", raising=False)
    monkeypatch.delenv("AZDO_TENANT", raising=False)
    monkeypatch.delenv("AZDO_PAT", raising=False)
    return config_dir, config_file


# ── TestAuth ──────────────────────────────────────────────────────

class TestAuth:

    def test_set_defaults_stores_values(self):
        result = set_defaults(
            organization="AMDigitalTech",
            project="Technology",
            tenant="adammatthewdigital.onmicrosoft.com",
        )
        assert result["status"] == "updated"
        config = load_config()
        assert config["organization"] == "AMDigitalTech"
        assert config["project"] == "Technology"
        assert config["tenant"] == "adammatthewdigital.onmicrosoft.com"

    def test_get_status_unconfigured(self):
        result = get_auth_status()
        assert result["configured"] is False
        assert result["authenticated"] is False

    @patch("cli_anything.azdo.core.auth.api_get")
    @patch("cli_anything.azdo.core.auth.get_auth_header")
    def test_get_status_configured_valid(self, mock_auth_header, mock_api_get):
        save_config({
            "organization": "AMDigitalTech",
            "project": "Technology",
            "tenant": "adammatthewdigital.onmicrosoft.com",
        })
        mock_auth_header.return_value = {"Authorization": "Bearer fake"}
        mock_api_get.return_value = {
            "id": "proj-id-123",
            "name": "Technology",
            "state": "wellFormed",
        }

        result = get_auth_status()
        assert result["configured"] is True
        assert result["authenticated"] is True
        assert result["project_name"] == "Technology"

    @patch("cli_anything.azdo.core.auth.api_get")
    @patch("cli_anything.azdo.core.auth.get_auth_header")
    def test_get_status_configured_invalid(self, mock_auth_header, mock_api_get):
        save_config({
            "organization": "AMDigitalTech",
            "project": "Technology",
            "tenant": "adammatthewdigital.onmicrosoft.com",
        })
        mock_auth_header.return_value = {"Authorization": "Bearer fake"}
        mock_api_get.side_effect = RuntimeError("401: Unauthorized")

        result = get_auth_status()
        assert result["configured"] is True
        assert result["authenticated"] is False
        assert "error" in result
