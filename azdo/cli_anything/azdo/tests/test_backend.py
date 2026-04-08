"""Tests for azdo_backend — config, token acquisition, BOM handling, API requests."""

import json
import os
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from cli_anything.azdo.utils.azdo_backend import (
    load_config,
    save_config,
    get_token,
    get_auth_header,
    api_get,
    api_post,
    api_patch,
    api_request,
    CONFIG_DIR,
    CONFIG_FILE,
    API_VERSION,
    AZDO_RESOURCE_ID,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Redirect config to a temp directory for every test."""
    config_dir = tmp_path / ".cli-anything-azdo"
    config_file = config_dir / "config.json"
    monkeypatch.setattr("cli_anything.azdo.utils.azdo_backend.CONFIG_DIR", config_dir)
    monkeypatch.setattr("cli_anything.azdo.utils.azdo_backend.CONFIG_FILE", config_file)
    # Clear env vars that could interfere
    monkeypatch.delenv("AZDO_ORG", raising=False)
    monkeypatch.delenv("AZDO_PROJECT", raising=False)
    monkeypatch.delenv("AZDO_TENANT", raising=False)
    monkeypatch.delenv("AZDO_PAT", raising=False)
    return config_dir, config_file


# ── TestBackendConfig ─────────────────────────────────────────────

class TestBackendConfig:

    def test_save_load_roundtrip(self):
        config = {"organization": "MyOrg", "project": "MyProject"}
        save_config(config)
        loaded = load_config()
        assert loaded == config

    def test_load_config_missing_file(self):
        assert load_config() == {}

    def test_config_file_permissions(self, isolated_config):
        _, config_file = isolated_config
        save_config({"test": True})
        mode = config_file.stat().st_mode & 0o777
        assert mode == 0o600

    def test_env_var_overrides(self, monkeypatch):
        save_config({"organization": "ConfigOrg", "project": "ConfigProj", "tenant": "ConfigTenant"})
        monkeypatch.setenv("AZDO_ORG", "EnvOrg")
        monkeypatch.setenv("AZDO_PROJECT", "EnvProject")
        monkeypatch.setenv("AZDO_TENANT", "EnvTenant")

        from cli_anything.azdo.utils.azdo_backend import get_org, get_project, get_tenant
        assert get_org() == "EnvOrg"
        assert get_project() == "EnvProject"
        assert get_tenant() == "EnvTenant"


# ── TestTokenAcquisition ─────────────────────────────────────────

class TestTokenAcquisition:

    @patch("cli_anything.azdo.utils.azdo_backend.subprocess.run")
    @patch("cli_anything.azdo.utils.azdo_backend.shutil.which", return_value="/usr/bin/az")
    def test_get_token_via_az_cli(self, mock_which, mock_run, monkeypatch):
        save_config({"tenant": "adammatthewdigital.onmicrosoft.com"})
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="eyJ0eXAiOiJKV1Q...\n",
            stderr="",
        )
        token = get_token()
        assert token == "eyJ0eXAiOiJKV1Q..."
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "/usr/bin/az"
        assert "get-access-token" in call_args
        assert AZDO_RESOURCE_ID in call_args

    @patch("cli_anything.azdo.utils.azdo_backend.subprocess.run")
    @patch("cli_anything.azdo.utils.azdo_backend.shutil.which", return_value="/usr/bin/az")
    def test_get_token_az_cli_failure(self, mock_which, mock_run, monkeypatch):
        save_config({"tenant": "adammatthewdigital.onmicrosoft.com"})
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ERROR: Please run 'az login'",
        )
        with pytest.raises(RuntimeError, match="az login"):
            get_token()

    @patch("cli_anything.azdo.utils.azdo_backend.shutil.which", return_value=None)
    def test_get_token_az_not_found(self, mock_which, monkeypatch):
        save_config({"tenant": "adammatthewdigital.onmicrosoft.com"})
        with pytest.raises(RuntimeError, match="Azure CLI.*not found"):
            get_token()

    def test_get_token_pat_fallback(self, monkeypatch):
        monkeypatch.setenv("AZDO_PAT", "my-secret-pat")
        header = get_auth_header()
        assert "Basic" in header["Authorization"]
        # Should be base64 of ":my-secret-pat"
        import base64
        expected = base64.b64encode(b":my-secret-pat").decode()
        assert header["Authorization"] == f"Basic {expected}"

    @patch("cli_anything.azdo.utils.azdo_backend.subprocess.run")
    def test_pat_takes_priority_over_az(self, mock_run, monkeypatch):
        monkeypatch.setenv("AZDO_PAT", "my-secret-pat")
        header = get_auth_header()
        assert "Basic" in header["Authorization"]
        mock_run.assert_not_called()


# ── TestBomHandling ───────────────────────────────────────────────

class TestBomHandling:

    @patch("cli_anything.azdo.utils.azdo_backend.requests.request")
    @patch("cli_anything.azdo.utils.azdo_backend.get_auth_header")
    def test_response_bom_stripped(self, mock_auth, mock_request, monkeypatch):
        save_config({"organization": "MyOrg", "project": "MyProject"})
        mock_auth.return_value = {"Authorization": "Bearer fake"}
        bom_json = b'\xef\xbb\xbf{"id": 123, "name": "Test"}'
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = bom_json
        mock_resp.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_resp

        result = api_get("/test/endpoint")
        assert result == {"id": 123, "name": "Test"}

    @patch("cli_anything.azdo.utils.azdo_backend.requests.request")
    @patch("cli_anything.azdo.utils.azdo_backend.get_auth_header")
    def test_response_without_bom(self, mock_auth, mock_request, monkeypatch):
        save_config({"organization": "MyOrg", "project": "MyProject"})
        mock_auth.return_value = {"Authorization": "Bearer fake"}
        normal_json = b'{"id": 456, "name": "Normal"}'
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = normal_json
        mock_resp.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_resp

        result = api_get("/test/endpoint")
        assert result == {"id": 456, "name": "Normal"}


# ── TestApiRequest ────────────────────────────────────────────────

class TestApiRequest:

    @patch("cli_anything.azdo.utils.azdo_backend.requests.request")
    @patch("cli_anything.azdo.utils.azdo_backend.get_auth_header")
    def test_api_get_includes_auth_header(self, mock_auth, mock_request):
        save_config({"organization": "MyOrg", "project": "MyProject"})
        mock_auth.return_value = {"Authorization": "Bearer test-token"}
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = b'{"value": []}'
        mock_resp.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_resp

        api_get("/test")
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer test-token"

    @patch("cli_anything.azdo.utils.azdo_backend.requests.request")
    @patch("cli_anything.azdo.utils.azdo_backend.get_auth_header")
    def test_api_get_includes_api_version(self, mock_auth, mock_request):
        save_config({"organization": "MyOrg", "project": "MyProject"})
        mock_auth.return_value = {"Authorization": "Bearer test-token"}
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = b'{"value": []}'
        mock_resp.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_resp

        api_get("/test")
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["params"]["api-version"] == API_VERSION

    @patch("cli_anything.azdo.utils.azdo_backend.requests.request")
    @patch("cli_anything.azdo.utils.azdo_backend.get_auth_header")
    def test_api_post_sends_json_body(self, mock_auth, mock_request):
        save_config({"organization": "MyOrg", "project": "MyProject"})
        mock_auth.return_value = {"Authorization": "Bearer test-token"}
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": 1}'
        mock_resp.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_resp

        body = {"title": "New Item"}
        api_post("/test", data=body)
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["json"] == body

    @patch("cli_anything.azdo.utils.azdo_backend.requests.request")
    @patch("cli_anything.azdo.utils.azdo_backend.get_auth_header")
    def test_api_patch_content_type(self, mock_auth, mock_request):
        save_config({"organization": "MyOrg", "project": "MyProject"})
        mock_auth.return_value = {"Authorization": "Bearer test-token"}
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": 1}'
        mock_resp.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_resp

        patch_ops = [{"op": "add", "path": "/fields/System.Title", "value": "Updated"}]
        api_patch("/test", data=patch_ops)
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["headers"]["Content-Type"] == "application/json-patch+json"

    @patch("cli_anything.azdo.utils.azdo_backend.requests.request")
    @patch("cli_anything.azdo.utils.azdo_backend.get_auth_header")
    def test_api_error_includes_message(self, mock_auth, mock_request):
        save_config({"organization": "MyOrg", "project": "MyProject"})
        mock_auth.return_value = {"Authorization": "Bearer test-token"}
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 404
        mock_resp.content = b'{"message": "Not found"}'
        mock_resp.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_resp

        with pytest.raises(RuntimeError, match="404"):
            api_get("/nonexistent")
