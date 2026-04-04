"""Domain management — organizational domains within a landscape.

Domains group model objects by business capability or bounded context.
"""

from cli_anything.icepanel.utils.icepanel_backend import (
    api_get,
    api_post,
    api_put,
    api_patch,
    api_delete,
    _get_default_landscape_id,
    _get_default_version_id,
)


def _lv(landscape_id: str | None, version_id: str | None) -> tuple[str, str]:
    lid = landscape_id or _get_default_landscape_id()
    if not lid:
        raise RuntimeError("Landscape ID required.")
    vid = version_id or _get_default_version_id()
    return lid, vid


def _base(lid: str, vid: str) -> str:
    return f"/landscapes/{lid}/versions/{vid}/domains"


def list_domains(landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """List all domains."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(_base(lid, vid))
    domains = data.get("domains", [])
    return {"count": len(domains), "domains": domains}


def create_domain(landscape_id: str | None = None, version_id: str | None = None, **kwargs) -> dict:
    """Create a domain."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_post(_base(lid, vid), {k: v for k, v in kwargs.items() if v is not None})
    return data.get("domain", data)


def get_domain(domain_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Get a domain."""
    lid, vid = _lv(landscape_id, version_id)
    data = api_get(f"{_base(lid, vid)}/{domain_id}")
    return data.get("domain", data)


def update_domain(domain_id: str, landscape_id: str | None = None, version_id: str | None = None, **kwargs) -> dict:
    """Update a domain."""
    lid, vid = _lv(landscape_id, version_id)
    body = {k: v for k, v in kwargs.items() if v is not None}
    if not body:
        raise ValueError("No fields provided.")
    data = api_patch(f"{_base(lid, vid)}/{domain_id}", body)
    return data.get("domain", data)


def delete_domain(domain_id: str, landscape_id: str | None = None, version_id: str | None = None) -> dict:
    """Delete a domain."""
    lid, vid = _lv(landscape_id, version_id)
    return api_delete(f"{_base(lid, vid)}/{domain_id}")
