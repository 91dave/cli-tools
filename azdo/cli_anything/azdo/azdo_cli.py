#!/usr/bin/env python3
"""Azure DevOps CLI — Work items, queries, and comments from the command line.

Usage:
    # Set defaults
    cli-anything-azdo auth set-defaults --org AMDigitalTech --project Technology --tenant adammatthewdigital.onmicrosoft.com

    # Check auth status
    cli-anything-azdo auth status

    # Interactive REPL
    cli-anything-azdo
"""

import sys
import os
import json
import shlex
import click

from cli_anything.azdo.core import auth as auth_mod
from cli_anything.azdo.core import workitems as workitems_mod
from cli_anything.azdo.core import wiql as wiql_mod
from cli_anything.azdo.core import comments as comments_mod

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
    """Azure DevOps CLI — Work items, queries, and comments.

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


@auth.command("set-defaults")
@click.option("--org", default=None, help="Azure DevOps organization name")
@click.option("--project", default=None, help="Azure DevOps project name")
@click.option("--tenant", default=None, help="Azure AD tenant name")
@handle_error
def auth_set_defaults(org, project, tenant):
    """Set default org/project/tenant."""
    result = auth_mod.set_defaults(org, project, tenant)
    output(result, "✓ Defaults updated.")


@auth.command("status")
@handle_error
def auth_status():
    """Check authentication status."""
    result = auth_mod.get_auth_status()
    output(result)


# ══════════════════════════════════════════════════════════════════
# WORKITEM COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group()
def workitem():
    """Work item operations."""
    pass


@workitem.command("show")
@click.argument("id", type=int)
@click.option("--field", multiple=True, help="Include extra field by reference name (repeatable)")
@handle_error
def workitem_show(id, field):
    """Show a work item by ID."""
    extra = field if field else None
    result = workitems_mod.get_workitem(id, extra_fields=extra)
    output(result, f"Work Item {id}")


@workitem.command("list")
@click.option("--state", default=None, help="Filter by state (e.g. Active, Closed)")
@click.option("--type", "work_item_type", default=None, help="Filter by type (e.g. Bug, Task)")
@click.option("--assigned-to", default=None, help="Filter by assignee (@Me for current user)")
@click.option("--area", default=None, help="Filter by area path")
@click.option("--iteration", default=None, help="Filter by iteration path")
@click.option("--top", default=None, type=int, help="Maximum number of results")
@handle_error
def workitem_list(state, work_item_type, assigned_to, area, iteration, top):
    """List work items matching filters."""
    results = workitems_mod.list_workitems(
        state=state,
        work_item_type=work_item_type,
        assigned_to=assigned_to,
        area=area,
        iteration=iteration,
        top=top,
    )
    output(results, f"{len(results)} work item(s) found")


@workitem.command("search")
@click.argument("text")
@click.option("--top", default=None, type=int, help="Maximum number of results")
@handle_error
def workitem_search(text, top):
    """Search work items by title text."""
    results = workitems_mod.search_workitems(text, top=top)
    output(results, f"{len(results)} work item(s) found")


@workitem.command("fields")
@click.argument("id", type=int)
@click.option("--name", multiple=True, help="Filter to specific field name(s) (repeatable)")
@handle_error
def workitem_fields(id, name):
    """Show all fields for a work item, including custom fields."""
    field_names = name if name else None
    result = workitems_mod.get_workitem_fields(id, field_names=field_names)
    output(result, f"Fields for Work Item {id}")


@workitem.command("children")
@click.argument("id", type=int)
@handle_error
def workitem_children(id):
    """List child work items of a parent."""
    results = workitems_mod.get_children(id)
    output(results, f"{len(results)} child work item(s)")


@workitem.command("update")
@click.argument("id", type=int)
@click.option("--state", default=None, help="Set work item state")
@click.option("--title", default=None, help="Set work item title")
@click.option("--assigned-to", default=None, help="Set assignee")
@click.option("--field", multiple=True, help="Set field as key=value (repeatable)")
@handle_error
def workitem_update(id, state, title, assigned_to, field):
    """Update a work item's fields."""
    fields = {}
    if state:
        fields["System.State"] = state
    if title:
        fields["System.Title"] = title
    if assigned_to:
        fields["System.AssignedTo"] = assigned_to
    for f in field:
        if "=" not in f:
            raise click.BadParameter(f"Field must be key=value, got: {f}")
        k, v = f.split("=", 1)
        fields[k] = v
    if not fields:
        raise click.UsageError("No fields specified. Use --state, --title, --assigned-to, or --field.")
    result = workitems_mod.update_workitem(id, fields)
    output(result, f"✓ Work item {id} updated")


@workitem.command("create")
@click.option("--type", "work_item_type", required=True, help="Work item type (e.g. Task, Bug)")
@click.option("--title", required=True, help="Work item title")
@click.option("--state", default=None, help="Initial state")
@click.option("--parent", "parent_id", default=None, type=int, help="Parent work item ID")
@click.option("--field", multiple=True, help="Set field as key=value (repeatable)")
@handle_error
def workitem_create(work_item_type, title, state, parent_id, field):
    """Create a new work item."""
    fields = {"System.Title": title}
    if state:
        fields["System.State"] = state
    for f in field:
        if "=" not in f:
            raise click.BadParameter(f"Field must be key=value, got: {f}")
        k, v = f.split("=", 1)
        fields[k] = v
    result = workitems_mod.create_workitem(work_item_type, fields, parent_id=parent_id)
    output(result, f"✓ Work item created: {result.get('id')}")


# ══════════════════════════════════════════════════════════════════
# COMMENT COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group()
def comment():
    """Work item comment operations."""
    pass


@comment.command("list")
@click.argument("work_item_id", type=int)
@handle_error
def comment_list(work_item_id):
    """List comments on a work item."""
    result = comments_mod.list_comments(work_item_id)
    if _json_output:
        output(result)
    else:
        if result["count"] == 0:
            click.echo("No comments.")
        else:
            click.echo(f"{result['count']} comment(s):")
            click.echo()
            for c in result["comments"]:
                click.echo(f"  [{c['author']}] ({c['date'][:16].replace('T', ' ')})")
                click.echo(f"    {c['text_plain']}")
                click.echo()


@comment.command("add")
@click.argument("work_item_id", type=int)
@click.argument("file", type=click.Path(exists=True, allow_dash=True))
@handle_error
def comment_add(work_item_id, file):
    """Add a comment to a work item from a markdown file.

    FILE is a path to a markdown file, or '-' to read from stdin.
    """
    if file == "-":
        text = click.get_text_stream("stdin").read()
    else:
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()
    result = comments_mod.add_comment(work_item_id, text)
    if _json_output:
        output(result)
    else:
        click.echo(f"✓ Comment {result['id']} added by {result['author']}")


# ══════════════════════════════════════════════════════════════════
# QUERY COMMANDS
# ══════════════════════════════════════════════════════════════════

@cli.group()
def query():
    """WIQL query operations."""
    pass


@query.command("run")
@click.argument("wiql")
@handle_error
def query_run(wiql):
    """Run a raw WIQL query."""
    results = wiql_mod.run_wiql(wiql)
    output(results, f"{len(results)} result(s)")


@query.command("mine")
@handle_error
def query_mine():
    """Get active work items assigned to me."""
    results = wiql_mod.get_my_workitems()
    output(results, f"{len(results)} work item(s) assigned to me")


# ══════════════════════════════════════════════════════════════════
# REPL
# ══════════════════════════════════════════════════════════════════

@cli.command()
@handle_error
def repl():
    """Start interactive REPL session."""
    from cli_anything.azdo.utils.repl_skin import ReplSkin

    global _repl_mode
    _repl_mode = True

    skin = ReplSkin("azdo", version="1.0.0")
    skin.print_banner()

    pt_session = skin.create_prompt_session()

    _repl_commands = {
        "auth":     "set-defaults|status",
        "workitem": "show|list|search|children|fields|update|create",
        "comment":  "list|add",
        "query":    "run|mine",
        "help":     "Show this help",
        "quit":     "Exit REPL",
    }

    # Check auth on start
    try:
        status = auth_mod.get_auth_status()
        if status.get("authenticated"):
            skin.success(f"Authenticated — {status.get('organization')}/{status.get('project')}")
        elif status.get("configured"):
            skin.warning("Configured but authentication failed. Check az login.")
        else:
            skin.info("Not configured. Run: auth set-defaults --org <ORG> --project <PROJECT> --tenant <TENANT>")
    except Exception:
        skin.info("Run 'auth set-defaults' to configure.")

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
