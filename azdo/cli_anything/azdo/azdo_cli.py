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
