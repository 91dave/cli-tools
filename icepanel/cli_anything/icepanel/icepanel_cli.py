#!/usr/bin/env python3
"""IcePanel CLI — Architecture visualization and C4 modelling from the command line.

This CLI wraps the IcePanel REST API v1 via API key authentication. It covers
the full architecture management lifecycle: organizations, landscapes, model
objects, connections, diagrams, flows, versions, tags, domains, and teams.

Usage:
    # Setup API key
    cli-anything-icepanel auth setup --api-key "<keyId>:<keySecret>"

    # Set defaults so you don't repeat IDs every time
    cli-anything-icepanel auth set-defaults --org-id <ID> --landscape-id <ID>

    # List landscapes
    cli-anything-icepanel org landscapes

    # List model objects
    cli-anything-icepanel object list

    # Interactive REPL
    cli-anything-icepanel
"""

import sys
import os
import json
import shlex
import click
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.icepanel.core import auth as auth_mod
from cli_anything.icepanel.core import organizations as org_mod
from cli_anything.icepanel.core import landscapes as land_mod
from cli_anything.icepanel.core import versions as ver_mod
from cli_anything.icepanel.core import model_objects as obj_mod
from cli_anything.icepanel.core import connections as conn_mod
from cli_anything.icepanel.core import diagrams as diag_mod
from cli_anything.icepanel.core import flows as flow_mod
from cli_anything.icepanel.core import tags as tag_mod
from cli_anything.icepanel.core import domains as dom_mod
from cli_anything.icepanel.core import teams as team_mod

# Global state
_json_output = False
_repl_mode = False


def output(data, message: str = ""):
    """Print output in JSON or human-readable format."""
    if _json_output:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if message:
            click.echo(message)
        if isinstance(data, dict):
            _print_dict(data)
        elif isinstance(data, list):
            _print_list(data)
        else:
            click.echo(str(data))


def _print_dict(d: dict, indent: int = 0):
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            click.echo(f"{prefix}{k}:")
            _print_dict(v, indent + 1)
        elif isinstance(v, list):
            click.echo(f"{prefix}{k}:")
            _print_list(v, indent + 1)
        else:
            click.echo(f"{prefix}{k}: {v}")


def _print_list(items: list, indent: int = 0):
    prefix = "  " * indent
    for i, item in enumerate(items):
        if isinstance(item, dict):
            click.echo(f"{prefix}[{i}]")
            _print_dict(item, indent + 1)
        else:
            click.echo(f"{prefix}- {item}")


def handle_error(func):
    """Decorator for consistent error handling."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if _json_output:
                click.echo(json.dumps({"error": str(e), "type": type(e).__name__}))
            else:
                click.echo(f"Error: {e}", err=True)
            if not _repl_mode:
                sys.exit(1)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ── Main CLI Group ──────────────────────────────────────────────
@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.pass_context
def cli(ctx, use_json):
    """IcePanel CLI — Architecture visualization from the command line.

    Run without a subcommand to enter interactive REPL mode.
    """
    global _json_output
    _json_output = use_json
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ══════════════════════════════════════════════════════════════════
# AUTH COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group()
def auth():
    """Authentication and configuration."""
    pass


@auth.command("setup")
@click.option("--api-key", required=True, help="IcePanel API key (keyId:keySecret)")
@click.option("--org-id", default=None, help="Default organization ID")
@click.option("--landscape-id", default=None, help="Default landscape ID")
@click.option("--version-id", default=None, help="Default version ID")
@handle_error
def auth_setup(api_key, org_id, landscape_id, version_id):
    """Configure API key and optional defaults."""
    result = auth_mod.setup_api_key(api_key, org_id, landscape_id, version_id)
    output(result, "✓ API key configured.")


@auth.command("set-defaults")
@click.option("--org-id", default=None, help="Default organization ID")
@click.option("--landscape-id", default=None, help="Default landscape ID")
@click.option("--version-id", default=None, help="Default version ID")
@handle_error
def auth_set_defaults(org_id, landscape_id, version_id):
    """Set default org/landscape/version IDs."""
    result = auth_mod.set_defaults(org_id, landscape_id, version_id)
    output(result, "✓ Defaults updated.")


@auth.command("status")
@handle_error
def auth_status():
    """Check authentication status."""
    result = auth_mod.get_auth_status()
    output(result)


@auth.command("logout")
@handle_error
def auth_logout():
    """Remove saved config and API key."""
    result = auth_mod.logout()
    output(result, "✓ Logged out.")


# ══════════════════════════════════════════════════════════════════
# ORGANIZATION COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group("org")
def org():
    """Organization management."""
    pass


@org.command("list")
@handle_error
def org_list():
    """List all organizations."""
    result = org_mod.list_organizations()
    output(result, f"Organizations ({result['count']}):")


@org.command("info")
@click.option("--org-id", default=None, help="Organization ID")
@handle_error
def org_info(org_id):
    """Get organization details."""
    result = org_mod.get_organization(org_id)
    output(result)


@org.command("landscapes")
@click.option("--org-id", default=None, help="Organization ID")
@handle_error
def org_landscapes(org_id):
    """List landscapes in an organization."""
    result = org_mod.list_landscapes(org_id)
    output(result, f"Landscapes ({result['count']}):")


@org.command("create-landscape")
@click.option("--name", "-n", required=True, help="Landscape name")
@click.option("--org-id", default=None, help="Organization ID")
@handle_error
def org_create_landscape(name, org_id):
    """Create a new landscape."""
    result = org_mod.create_landscape(name, org_id)
    output(result, f"✓ Landscape created: {name}")


@org.command("technologies")
@click.option("--org-id", default=None, help="Organization ID")
@handle_error
def org_technologies(org_id):
    """List the technology catalog."""
    result = org_mod.list_technologies(org_id)
    output(result, f"Technologies ({result['count']}):")


@org.command("users")
@click.option("--org-id", default=None, help="Organization ID")
@handle_error
def org_users(org_id):
    """List organization users."""
    result = org_mod.list_users(org_id)
    output(result)


@org.command("invite")
@click.option("--email", "-e", required=True, help="User email")
@click.option("--permission", "-p", type=click.Choice(["admin", "editor", "viewer"]),
              default="editor", help="Permission level")
@click.option("--org-id", default=None, help="Organization ID")
@handle_error
def org_invite(email, permission, org_id):
    """Invite a user to the organization."""
    result = org_mod.create_user_invite(email, permission, org_id)
    output(result, f"✓ Invited {email} as {permission}")


# ══════════════════════════════════════════════════════════════════
# LANDSCAPE COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group("landscape")
def landscape():
    """Landscape management."""
    pass


@landscape.command("info")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@handle_error
def landscape_info(landscape_id):
    """Get landscape details."""
    result = land_mod.get_landscape(landscape_id)
    output(result)


@landscape.command("update")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--name", "-n", default=None, help="New name")
@handle_error
def landscape_update(landscape_id, name):
    """Update landscape properties."""
    result = land_mod.update_landscape(landscape_id, name=name)
    output(result, "✓ Landscape updated.")


@landscape.command("delete")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--confirm", is_flag=True, help="Skip confirmation")
@handle_error
def landscape_delete(landscape_id, confirm):
    """Delete a landscape permanently."""
    if not confirm and not _repl_mode:
        click.confirm("Delete this landscape? This cannot be undone.", abort=True)
    result = land_mod.delete_landscape(landscape_id)
    output(result, "✓ Landscape deleted.")


@landscape.command("duplicate")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@handle_error
def landscape_duplicate(landscape_id):
    """Duplicate a landscape."""
    result = land_mod.duplicate_landscape(landscape_id)
    output(result, "✓ Landscape duplicated.")


@landscape.command("export")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def landscape_export(landscape_id, version_id):
    """Start an async landscape export."""
    result = land_mod.export_landscape(landscape_id, version_id)
    output(result, "✓ Export started. Poll with: landscape export-status")


@landscape.command("export-status")
@click.argument("export_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def landscape_export_status(export_id, landscape_id, version_id):
    """Check async export status."""
    result = land_mod.export_status(export_id, landscape_id, version_id)
    output(result)


@landscape.command("logs")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--performed-by", type=click.Choice(["user", "api-key"]),
              default=None, help="Filter by performer type")
@click.option("--limit", default=20, help="Max results")
@handle_error
def landscape_logs(landscape_id, performed_by, limit):
    """List recent action logs."""
    result = land_mod.list_action_logs(landscape_id, performed_by, limit)
    output(result, f"Action logs ({result['count']}):")


@landscape.command("search")
@click.argument("query")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def landscape_search(query, landscape_id, version_id):
    """Search within a landscape."""
    result = land_mod.search(query, landscape_id, version_id)
    output(result)


# ══════════════════════════════════════════════════════════════════
# VERSION COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group("version")
def version():
    """Version/snapshot management."""
    pass


@version.command("list")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@handle_error
def version_list(landscape_id):
    """List all versions."""
    result = ver_mod.list_versions(landscape_id)
    output(result, f"Versions ({result['count']}):")


@version.command("create")
@click.option("--name", "-n", required=True, help="Version name")
@click.option("--notes", default="", help="Release notes")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@handle_error
def version_create(name, notes, landscape_id):
    """Create a version (snapshot/tag)."""
    result = ver_mod.create_version(name, notes, landscape_id)
    output(result, f"✓ Version created: {name}")


@version.command("info")
@click.option("--version-id", "-v", default=None, help="Version ID")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@handle_error
def version_info(version_id, landscape_id):
    """Get version details."""
    result = ver_mod.get_version(version_id, landscape_id)
    output(result)


@version.command("delete")
@click.argument("version_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@handle_error
def version_delete(version_id, landscape_id):
    """Delete a version."""
    result = ver_mod.delete_version(version_id, landscape_id)
    output(result, "✓ Version deleted.")


# ══════════════════════════════════════════════════════════════════
# MODEL OBJECT COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group("object")
def model_object():
    """Model objects (systems, apps, stores, actors, components, groups)."""
    pass


@model_object.command("list")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@click.option("--type", "-t", "type_filter", default=None,
              type=click.Choice(["system", "app", "store", "actor", "component", "group"]),
              help="Filter by object type")
@click.option("--name", "-n", "name_filter", default=None, help="Filter by name (substring)")
@click.option("--tag", "tag_filter", default=None, help="Filter by tag ID")
@click.option("--external/--internal", "external_filter", default=None, help="Filter by external/internal")
@handle_error
def object_list(landscape_id, version_id, type_filter, name_filter, tag_filter, external_filter):
    """List model objects with optional filters."""
    result = obj_mod.list_objects(landscape_id, version_id,
                                  name_filter=name_filter, type_filter=type_filter,
                                  tag_id_filter=tag_filter, external_filter=external_filter)
    output(result, f"Model objects ({result['count']}):")


@model_object.command("create")
@click.option("--name", "-n", required=True, help="Object name")
@click.option("--type", "-t", "obj_type", required=True,
              type=click.Choice(["system", "app", "store", "actor", "component", "group"]),
              help="Object type")
@click.option("--parent-id", default=None, help="Parent object ID (null for root)")
@click.option("--description", "-d", default=None, help="Description")
@click.option("--caption", default=None, help="Short caption")
@click.option("--external", is_flag=True, default=None, help="Mark as external")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_create(name, obj_type, parent_id, description, caption, external,
                  landscape_id, version_id):
    """Create a model object."""
    kwargs = {}
    if description:
        kwargs["description"] = description
    if caption:
        kwargs["caption"] = caption
    if external:
        kwargs["external"] = external
    result = obj_mod.create_object(name, obj_type, parent_id, landscape_id, version_id, **kwargs)
    output(result, f"✓ Created {obj_type}: {name}")


@model_object.command("info")
@click.argument("object_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_info(object_id, landscape_id, version_id):
    """Get model object details."""
    result = obj_mod.get_object(object_id, landscape_id, version_id)
    output(result)


@model_object.command("update")
@click.argument("object_id")
@click.option("--name", "-n", default=None, help="New name")
@click.option("--description", "-d", default=None, help="New description")
@click.option("--caption", default=None, help="New caption")
@click.option("--status", default=None, help="New status")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_update(object_id, name, description, caption, status, landscape_id, version_id):
    """Update a model object."""
    kwargs = {}
    if name:
        kwargs["name"] = name
    if description:
        kwargs["description"] = description
    if caption:
        kwargs["caption"] = caption
    if status:
        kwargs["status"] = status
    result = obj_mod.update_object(object_id, landscape_id, version_id, **kwargs)
    output(result, f"✓ Object {object_id} updated.")


@model_object.command("delete")
@click.argument("object_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_delete(object_id, landscape_id, version_id):
    """Delete a model object (cascades to children and connections)."""
    result = obj_mod.delete_object(object_id, landscape_id, version_id)
    output(result, f"✓ Object {object_id} deleted.")


@model_object.command("dependencies")
@click.argument("object_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_dependencies(object_id, landscape_id, version_id):
    """Export a model object's dependencies as JSON."""
    result = obj_mod.export_dependencies_json(object_id, landscape_id, version_id)
    output(result)


@model_object.command("export-csv")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_export_csv(landscape_id, version_id):
    """Export all model objects as CSV."""
    result = obj_mod.export_objects_csv(landscape_id, version_id)
    output(result)


@model_object.group("tag")
def object_tag():
    """Manage tags on model objects."""
    pass


@object_tag.command("add")
@click.argument("object_id")
@click.option("--tag-id", "-t", required=True, multiple=True, help="Tag ID(s) to add")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_tag_add(object_id, tag_id, landscape_id, version_id):
    """Add one or more tags to a model object."""
    result = obj_mod.add_tags(object_id, list(tag_id),
                              landscape_id=landscape_id, version_id=version_id)
    output(result, f"\u2713 Added {len(tag_id)} tag(s) to {object_id}")


@object_tag.command("remove")
@click.argument("object_id")
@click.option("--tag-id", "-t", required=True, multiple=True, help="Tag ID(s) to remove")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_tag_remove(object_id, tag_id, landscape_id, version_id):
    """Remove one or more tags from a model object."""
    result = obj_mod.remove_tags(object_id, list(tag_id),
                                 landscape_id=landscape_id, version_id=version_id)
    output(result, f"\u2713 Removed {len(tag_id)} tag(s) from {object_id}")


@object_tag.command("list")
@click.argument("object_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_tag_list(object_id, landscape_id, version_id):
    """List tags on a model object (resolved to names)."""
    obj = obj_mod.get_object(object_id, landscape_id, version_id)
    tag_ids = obj.get("tag_ids", [])
    if not tag_ids:
        output({"object_id": object_id, "count": 0, "tags": []},
               f"No tags on {object_id}")
        return
    tags = []
    all_tags = tag_mod.list_tags(landscape_id, version_id)
    tag_map = {t["id"]: t for t in all_tags.get("tags", [])}
    for tid in tag_ids:
        if tid in tag_map:
            tags.append(tag_map[tid])
        else:
            tags.append({"id": tid, "name": "unknown"})
    output({"object_id": object_id, "count": len(tags), "tags": tags},
           f"Tags ({len(tags)}) on {object_id}:")


@model_object.group("link")
def object_link():
    """Manage links (reality links) on model objects."""
    pass


@object_link.command("list")
@click.argument("object_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_link_list(object_id, landscape_id, version_id):
    """List all links on a model object."""
    result = obj_mod.list_links(object_id, landscape_id, version_id)
    output(result, f"Links ({result['count']}) on {object_id}:")


@object_link.command("add")
@click.argument("object_id")
@click.option("--url", "-u", required=True, help="Link URL")
@click.option("--name", "-n", default=None, help="Friendly name for the link")
@click.option("--index", "-i", type=int, default=None, help="Ordering index")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_link_add(object_id, url, name, index, landscape_id, version_id):
    """Add a link to a model object."""
    result = obj_mod.add_link(object_id, url, custom_name=name, index=index,
                              landscape_id=landscape_id, version_id=version_id)
    output(result, f"\u2713 Link added to {object_id}")


@object_link.command("update")
@click.argument("object_id")
@click.argument("link_id")
@click.option("--url", "-u", default=None, help="New URL")
@click.option("--name", "-n", default=None, help="New friendly name")
@click.option("--index", "-i", type=int, default=None, help="New ordering index")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_link_update(object_id, link_id, url, name, index, landscape_id, version_id):
    """Update an existing link on a model object."""
    result = obj_mod.update_link(object_id, link_id, url=url, custom_name=name,
                                  index=index, landscape_id=landscape_id,
                                  version_id=version_id)
    output(result, f"\u2713 Link {link_id} updated on {object_id}")


@object_link.command("remove")
@click.argument("object_id")
@click.argument("link_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def object_link_remove(object_id, link_id, landscape_id, version_id):
    """Remove a link from a model object."""
    result = obj_mod.remove_link(object_id, link_id, landscape_id=landscape_id,
                                  version_id=version_id)
    output(result, f"\u2713 Link {link_id} removed from {object_id}")


# ══════════════════════════════════════════════════════════════════
# CONNECTION COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group("connection")
def connection():
    """Model connections between objects."""
    pass


@connection.command("list")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@click.option("--name", "-n", "name_filter", default=None, help="Filter by name (substring)")
@click.option("--origin", "origin_filter", default=None, help="Filter by origin object ID")
@click.option("--target", "target_filter", default=None, help="Filter by target object ID")
@handle_error
def connection_list(landscape_id, version_id, name_filter, origin_filter, target_filter):
    """List connections with optional filters."""
    result = conn_mod.list_connections(landscape_id, version_id,
                                       name_filter=name_filter,
                                       origin_filter=origin_filter,
                                       target_filter=target_filter)
    output(result, f"Connections ({result['count']}):")


@connection.command("create")
@click.option("--origin-id", required=True, help="Source object ID")
@click.option("--target-id", required=True, help="Target object ID")
@click.option("--name", "-n", default="", help="Connection label")
@click.option("--description", "-d", default=None, help="Description")
@click.option("--direction", default="outgoing", help="Direction (default: outgoing)")
@click.option("--add-to-diagram", default=None, help="Also add to this diagram ID")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def connection_create(origin_id, target_id, name, description, direction,
                     add_to_diagram, landscape_id, version_id):
    """Create a connection between two objects."""
    kwargs = {}
    if description:
        kwargs["description"] = description
    result = conn_mod.create_connection(origin_id, target_id, name, direction,
                                        landscape_id, version_id, **kwargs)
    output(result, f"✓ Connection created: {origin_id} → {target_id}")
    if add_to_diagram and result.get("id"):
        # Resolve origin/target diagram IDs from the diagram
        resolved = diag_mod.resolve_content(add_to_diagram, landscape_id, version_id)
        origin_diag = next((o["diagram_id"] for o in resolved["objects"] if o["model_id"] == origin_id), None)
        target_diag = next((o["diagram_id"] for o in resolved["objects"] if o["model_id"] == target_id), None)
        if origin_diag and target_diag:
            diag_result = diag_mod.add_connection_to_diagram(
                add_to_diagram, result["id"], origin_diag, target_diag,
                landscape_id=landscape_id, version_id=version_id)
            output(diag_result, f"✓ Added to diagram {add_to_diagram}")


@connection.command("info")
@click.argument("connection_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def connection_info(connection_id, landscape_id, version_id):
    """Get connection details."""
    result = conn_mod.get_connection(connection_id, landscape_id, version_id)
    output(result)


@connection.command("update")
@click.argument("connection_id")
@click.option("--name", "-n", default=None, help="New label")
@click.option("--description", "-d", default=None, help="New description")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def connection_update(connection_id, name, description, landscape_id, version_id):
    """Update a connection."""
    kwargs = {}
    if name:
        kwargs["name"] = name
    if description:
        kwargs["description"] = description
    result = conn_mod.update_connection(connection_id, landscape_id, version_id, **kwargs)
    output(result, f"✓ Connection {connection_id} updated.")


@connection.command("delete")
@click.argument("connection_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def connection_delete(connection_id, landscape_id, version_id):
    """Delete a connection."""
    result = conn_mod.delete_connection(connection_id, landscape_id, version_id)
    output(result, f"✓ Connection deleted.")


@connection.command("generate-description")
@click.argument("connection_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def connection_gen_desc(connection_id, landscape_id, version_id):
    """Generate an AI description for a connection."""
    result = conn_mod.generate_description(connection_id, landscape_id, version_id)
    output(result)


@connection.command("export-csv")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def connection_export_csv(landscape_id, version_id):
    """Export all connections as CSV."""
    result = conn_mod.export_csv(landscape_id, version_id)
    output(result)


# ══════════════════════════════════════════════════════════════════
# DIAGRAM COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group("diagram")
def diagram():
    """Diagram management."""
    pass


@diagram.command("list")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def diagram_list(landscape_id, version_id):
    """List all diagrams."""
    result = diag_mod.list_diagrams(landscape_id, version_id)
    output(result, f"Diagrams ({result['count']}):")


@diagram.command("info")
@click.argument("diagram_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def diagram_info(diagram_id, landscape_id, version_id):
    """Get diagram details."""
    result = diag_mod.get_diagram(diagram_id, landscape_id, version_id)
    output(result)


@diagram.command("delete")
@click.argument("diagram_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def diagram_delete(diagram_id, landscape_id, version_id):
    """Delete a diagram."""
    result = diag_mod.delete_diagram(diagram_id, landscape_id, version_id)
    output(result, "✓ Diagram deleted.")


@diagram.command("content")
@click.argument("diagram_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def diagram_content(diagram_id, landscape_id, version_id):
    """Get diagram content."""
    result = diag_mod.get_content(diagram_id, landscape_id, version_id)
    output(result)


@diagram.command("resolve")
@click.argument("diagram_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def diagram_resolve(diagram_id, landscape_id, version_id):
    """Show all objects and connections on a diagram with resolved model names."""
    result = diag_mod.resolve_content(diagram_id, landscape_id, version_id)
    output(result, f"Objects ({result['object_count']}), Connections ({result['connection_count']}):")


@diagram.command("lookup")
@click.argument("diagram_id")
@click.argument("name")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def diagram_lookup(diagram_id, name, landscape_id, version_id):
    """Find diagram-specific IDs for a model object or connection by name."""
    result = diag_mod.lookup_diagram_id(diagram_id, name, landscape_id, version_id)
    output(result)


@diagram.command("add-connection")
@click.argument("diagram_id")
@click.option("--model-connection-id", required=True, help="Model connection ID")
@click.option("--origin-diagram-id", required=True, help="Origin object's diagram ID")
@click.option("--target-diagram-id", required=True, help="Target object's diagram ID")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def diagram_add_connection(diagram_id, model_connection_id, origin_diagram_id,
                          target_diagram_id, landscape_id, version_id):
    """Add an existing model connection to a diagram."""
    result = diag_mod.add_connection_to_diagram(
        diagram_id, model_connection_id, origin_diagram_id, target_diagram_id,
        landscape_id=landscape_id, version_id=version_id)
    output(result, "✓ Connection added to diagram.")


@diagram.command("export-image")
@click.argument("diagram_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def diagram_export_image(diagram_id, landscape_id, version_id):
    """Start async diagram image export."""
    result = diag_mod.export_image(diagram_id, landscape_id, version_id)
    output(result, "✓ Image export started.")


# ══════════════════════════════════════════════════════════════════
# FLOW COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group("flow")
def flow():
    """Flow (sequence diagram) management."""
    pass


@flow.command("list")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@click.option("--name", "-n", "name_filter", default=None, help="Filter by name (substring)")
@click.option("--diagram-id", "-d", default=None, help="Filter by diagram ID")
@click.option("--pinned/--unpinned", "pinned_filter", default=None, help="Filter by pinned status")
@handle_error
def flow_list(landscape_id, version_id, name_filter, diagram_id, pinned_filter):
    """List all flows with optional filters."""
    result = flow_mod.list_flows(landscape_id, version_id,
                                  name_filter=name_filter,
                                  diagram_id_filter=diagram_id,
                                  pinned_filter=pinned_filter)
    output(result, f"Flows ({result['count']}):")


@flow.command("info")
@click.argument("flow_id")
@click.option("--resolve", is_flag=True, help="Resolve diagram IDs to human-readable names")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_info(flow_id, resolve, landscape_id, version_id):
    """Get flow details. Use --resolve to show human-readable step names."""
    if resolve:
        result = flow_mod.resolve_flow_steps(flow_id, landscape_id, version_id)
    else:
        result = flow_mod.get_flow(flow_id, landscape_id, version_id)
    output(result)


@flow.command("create")
@click.option("--name", "-n", required=True, help="Flow name")
@click.option("--diagram-id", "-d", required=True, help="Diagram ID to attach flow to")
@click.option("--from-file", "-f", type=click.Path(exists=True),
              help="JSON file containing step definitions")
@click.option("--resolve-names", is_flag=True,
              help="Resolve object/connection names to diagram IDs")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_create(name, diagram_id, from_file, resolve_names, landscape_id, version_id):
    """Create a flow, optionally with steps from a JSON file."""
    steps = None
    if from_file:
        with open(from_file, "r") as f:
            data = json.loads(f.read())
            steps = data.get("steps", data) if isinstance(data, dict) else data
    result = flow_mod.create_flow(name, diagram_id, steps=steps,
                                   resolve_names=resolve_names,
                                   landscape_id=landscape_id, version_id=version_id)
    output(result, f"✓ Flow created: {name}")


@flow.command("delete")
@click.argument("flow_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_delete(flow_id, landscape_id, version_id):
    """Delete a flow."""
    result = flow_mod.delete_flow(flow_id, landscape_id, version_id)
    output(result, "✓ Flow deleted.")


@flow.command("update")
@click.argument("flow_id")
@click.option("--name", "-n", default=None, help="New flow name")
@click.option("--pinned/--unpinned", default=None, help="Pin or unpin the flow")
@click.option("--show-all-steps/--no-show-all-steps", "show_all_steps", default=None,
              help="Show all steps on diagram")
@click.option("--show-connection-names/--no-show-connection-names", "show_connection_names",
              default=None, help="Show connection names on diagram")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_update(flow_id, name, pinned, show_all_steps, show_connection_names,
               landscape_id, version_id):
    """Update flow properties (name, pinned, display options)."""
    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if pinned is not None:
        kwargs["pinned"] = pinned
    if show_all_steps is not None:
        kwargs["showAllSteps"] = show_all_steps
    if show_connection_names is not None:
        kwargs["showConnectionNames"] = show_connection_names
    result = flow_mod.update_flow(flow_id, landscape_id, version_id, **kwargs)
    output(result, f"✓ Flow {flow_id} updated.")


@flow.command("steps")
@click.argument("flow_id")
@click.option("--resolve", is_flag=True, help="Resolve diagram IDs to human-readable names")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_steps(flow_id, resolve, landscape_id, version_id):
    """List steps of a flow. Use --resolve for human-readable names."""
    result = flow_mod.list_steps(flow_id, resolve=resolve,
                                  landscape_id=landscape_id, version_id=version_id)
    output(result, f"Steps ({result['count']}) in {flow_id}:")


@flow.command("add-step")
@click.argument("flow_id")
@click.option("--from-file", "-f", type=click.Path(exists=True),
              help="JSON file containing step definition(s)")
@click.option("--type", "-t", "step_type",
              type=click.Choice(["outgoing", "self-action", "introduction",
                                 "information", "conclusion", "alternate-path",
                                 "parallel-path", "reply", "subflow"]),
              default=None, help="Step type (for inline definition)")
@click.option("--description", "-d", default=None, help="Step description")
@click.option("--detailed-description", default=None, help="Long description")
@click.option("--origin-id", default=None, help="Origin diagram object ID")
@click.option("--target-id", default=None, help="Target diagram object ID")
@click.option("--via-id", default=None, help="Connection diagram ID")
@click.option("--origin", "origin_name", default=None, help="Origin object name (use with --resolve-names)")
@click.option("--target", "target_name", default=None, help="Target object name (use with --resolve-names)")
@click.option("--via", "via_name", default=None, help="Connection name (use with --resolve-names)")
@click.option("--index", "-i", type=int, default=None, help="Step index")
@click.option("--resolve-names", is_flag=True, help="Resolve object/connection names to diagram IDs")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_add_step(flow_id, from_file, step_type, description, detailed_description,
                  origin_id, target_id, via_id, origin_name, target_name, via_name,
                  index, resolve_names, landscape_id, version_id):
    """Add steps to a flow. Use --from-file for bulk or inline options for a single step."""
    if from_file:
        with open(from_file, "r") as f:
            steps = json.loads(f.read())
        result = flow_mod.add_flow_steps(flow_id, steps, landscape_id, version_id)
        output(result, "✓ Steps added from file.")
    elif step_type:
        result = flow_mod.add_inline_step(
            flow_id, step_type=step_type,
            description=description or "",
            detailed_description=detailed_description,
            origin_id=origin_id, target_id=target_id, via_id=via_id,
            origin_name=origin_name, target_name=target_name, via_name=via_name,
            index=index, resolve_names=resolve_names,
            landscape_id=landscape_id, version_id=version_id,
        )
        output(result, "✓ Step added.")
    else:
        raise click.UsageError("Provide --from-file or --type for inline step definition.")


@flow.command("update-step")
@click.argument("flow_id")
@click.argument("step_id")
@click.option("--description", "-d", default=None, help="Update description")
@click.option("--detailed-description", default=None, help="Update long description")
@click.option("--origin-id", default=None, help="Update origin diagram ID")
@click.option("--target-id", default=None, help="Update target diagram ID")
@click.option("--via-id", default=None, help="Set the connection (viaId)")
@click.option("--origin", "origin_name", default=None, help="Origin object name (use with --resolve-names)")
@click.option("--target", "target_name", default=None, help="Target object name (use with --resolve-names)")
@click.option("--via", "via_name", default=None, help="Connection name (use with --resolve-names)")
@click.option("--resolve-names", is_flag=True, help="Resolve object/connection names to diagram IDs")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_update_step(flow_id, step_id, description, detailed_description,
                    origin_id, target_id, via_id, origin_name, target_name,
                    via_name, resolve_names, landscape_id, version_id):
    """Update a single step in a flow. Supports name resolution with --resolve-names."""
    result = flow_mod.update_flow_step(
        flow_id, step_id,
        description=description,
        detailed_description=detailed_description,
        origin_id=origin_id, target_id=target_id, via_id=via_id,
        origin_name=origin_name, target_name=target_name, via_name=via_name,
        resolve_names=resolve_names,
        landscape_id=landscape_id, version_id=version_id,
    )
    output(result, f"✓ Step {step_id} updated.")


@flow.command("remove-step")
@click.argument("flow_id")
@click.argument("step_ids", nargs=-1, required=True)
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_remove_step(flow_id, step_ids, landscape_id, version_id):
    """Remove steps from a flow by ID."""
    result = flow_mod.remove_flow_steps(flow_id, list(step_ids), landscape_id, version_id)
    output(result, f"✓ Removed {len(step_ids)} step(s).")


@flow.command("export-mermaid")
@click.argument("flow_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_export_mermaid(flow_id, landscape_id, version_id):
    """Export a flow as Mermaid syntax."""
    result = flow_mod.export_mermaid(flow_id, landscape_id, version_id)
    output(result)


@flow.command("export-text")
@click.argument("flow_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_export_text(flow_id, landscape_id, version_id):
    """Export a flow as plain text."""
    result = flow_mod.export_text(flow_id, landscape_id, version_id)
    output(result)


@flow.command("export-code")
@click.argument("flow_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def flow_export_code(flow_id, landscape_id, version_id):
    """Export a flow as code."""
    result = flow_mod.export_code(flow_id, landscape_id, version_id)
    output(result)


# ══════════════════════════════════════════════════════════════════
# TAG COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group("tag")
def tag():
    """Tag and tag group management."""
    pass


@tag.command("list")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def tag_list(landscape_id, version_id):
    """List all tags."""
    result = tag_mod.list_tags(landscape_id, version_id)
    output(result, f"Tags ({result['count']}):")


@tag.command("info")
@click.argument("tag_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def tag_info(tag_id, landscape_id, version_id):
    """Get tag details."""
    result = tag_mod.get_tag(tag_id, landscape_id, version_id)
    output(result)


@tag.command("objects")
@click.argument("tag_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def tag_objects(tag_id, landscape_id, version_id):
    """List all objects with a given tag (full details)."""
    result = tag_mod.get_tagged_objects(tag_id, landscape_id, version_id)
    output(result, f"Tagged objects ({result['count']}):")


@tag.command("groups")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def tag_groups(landscape_id, version_id):
    """List tag groups."""
    result = tag_mod.list_tag_groups(landscape_id, version_id)
    output(result)


# ══════════════════════════════════════════════════════════════════
# DOMAIN COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group("domain")
def domain():
    """Domain management."""
    pass


@domain.command("list")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def domain_list(landscape_id, version_id):
    """List all domains."""
    result = dom_mod.list_domains(landscape_id, version_id)
    output(result, f"Domains ({result['count']}):")


@domain.command("info")
@click.argument("domain_id")
@click.option("--landscape-id", "-l", default=None, help="Landscape ID")
@click.option("--version-id", "-v", default=None, help="Version ID")
@handle_error
def domain_info(domain_id, landscape_id, version_id):
    """Get domain details."""
    result = dom_mod.get_domain(domain_id, landscape_id, version_id)
    output(result)


# ══════════════════════════════════════════════════════════════════
# TEAM COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group("team")
def team():
    """Team management."""
    pass


@team.command("list")
@click.option("--org-id", default=None, help="Organization ID")
@handle_error
def team_list(org_id):
    """List all teams."""
    result = team_mod.list_teams(org_id)
    output(result, f"Teams ({result['count']}):")


@team.command("info")
@click.argument("team_id")
@click.option("--org-id", default=None, help="Organization ID")
@handle_error
def team_info(team_id, org_id):
    """Get team details."""
    result = team_mod.get_team(team_id, org_id)
    output(result)


@team.command("create")
@click.option("--name", "-n", required=True, help="Team name")
@click.option("--color", "-c", default="blue", help="Team color")
@click.option("--org-id", default=None, help="Organization ID")
@handle_error
def team_create(name, color, org_id):
    """Create a team."""
    result = team_mod.create_team(name, color, org_id)
    output(result, f"✓ Team created: {name}")


@team.command("delete")
@click.argument("team_id")
@click.option("--org-id", default=None, help="Organization ID")
@handle_error
def team_delete(team_id, org_id):
    """Delete a team."""
    result = team_mod.delete_team(team_id, org_id)
    output(result, "✓ Team deleted.")


# ══════════════════════════════════════════════════════════════════
# REPL
# ══════════════════════════════════════════════════════════════════

@cli.command()
@handle_error
def repl():
    """Start interactive REPL session."""
    from cli_anything.icepanel.utils.repl_skin import ReplSkin

    global _repl_mode
    _repl_mode = True

    skin = ReplSkin("icepanel", version="1.0.0")
    skin.print_banner()

    pt_session = skin.create_prompt_session()

    _repl_commands = {
        "auth":       "setup|set-defaults|status|logout",
        "org":        "list|info|landscapes|create-landscape|technologies|users|invite",
        "landscape":  "info|update|delete|duplicate|export|export-status|logs|search",
        "version":    "list|create|info|delete",
        "object":     "list [--type|--name|--tag|--external]|create|info|update|delete|dependencies|export-csv|tag list|tag add|tag remove|link list|link add|link update|link remove",
        "connection": "list [--name|--origin|--target]|create [--add-to-diagram]|info|update|delete|generate-description|export-csv",
        "diagram":    "list|info|delete|content|resolve|lookup|add-connection|export-image",
        "flow":       "list [--name|--diagram-id|--pinned]|create [--from-file]|info [--resolve]|update|delete|steps [--resolve]|add-step [--from-file|--type]|update-step [--resolve-names]|remove-step|export-mermaid|export-text|export-code",
        "tag":        "list|info|objects|groups",
        "domain":     "list|info",
        "team":       "list|info|create|delete",
        "help":       "Show this help",
        "quit":       "Exit REPL",
    }

    # Check auth on start
    try:
        status = auth_mod.get_auth_status()
        if status.get("authenticated"):
            skin.success(f"Authenticated ({status.get('organizations_count', 0)} organizations)")
            if status.get("organization_id"):
                skin.info(f"Default org: {status['organization_id']}")
            if status.get("landscape_id"):
                skin.info(f"Default landscape: {status['landscape_id']}")
        elif status.get("configured"):
            skin.warning("API key configured but validation failed. Check your key.")
        else:
            skin.info("Not configured. Run: auth setup --api-key <KEY>")
    except Exception:
        skin.info("Run 'auth setup --api-key <KEY>' to configure.")

    while True:
        try:
            line = skin.get_input(pt_session, context="")
            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                skin.print_goodbye()
                break
            if line.lower() == "help":
                skin.help(_repl_commands)
                continue

            try:
                args = shlex.split(line)
            except ValueError:
                args = line.split()
            try:
                cli.main(args, standalone_mode=False)
            except SystemExit:
                pass
            except click.exceptions.UsageError as e:
                skin.warning(f"Usage error: {e}")
            except Exception as e:
                skin.error(f"{e}")

        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

    _repl_mode = False


# ── Entry Point ──────────────────────────────────────────────────
def main():
    cli()


if __name__ == "__main__":
    main()
