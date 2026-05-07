---
name: >-
  cli-anything-azdo
description: >-
  Command-line interface for Azure DevOps — manage work items, run WIQL queries, and manage comments via the Azure DevOps REST API.
---

# cli-anything-azdo

CLI harness for **Azure DevOps** — work items, queries, and comments from the command line.

## Installation

```bash
pip install -e .   # from azdo/
```

**Prerequisites:**
- Python 3.10+
- Azure CLI installed and logged in: `az login --tenant your-tenant.onmicrosoft.com`

## Usage

```bash
# Setup
cli-anything-azdo auth set-defaults --org AMDigitalTech --project Technology --tenant your-tenant.onmicrosoft.com

# Check auth
cli-anything-azdo auth status

# JSON output for agents
cli-anything-azdo --json workitem show 12345
cli-anything-azdo --json query mine

# Interactive REPL
cli-anything-azdo
```

## Command Groups

### Auth
| Command | Description |
|---------|-------------|
| `set-defaults` | Set default org/project/tenant |
| `status` | Check authentication status |

### Workitem
| Command | Description |
|---------|-------------|
| `show <id>` | Show a work item by ID |
| `list` | List work items with filters (`--state`, `--type`, `--assigned-to`, `--area`, `--iteration`, `--top`) |
| `search <text>` | Search work items by title |
| `children <id>` | List child work items of a parent |
| `update <id>` | Update fields (`--state`, `--title`, `--assigned-to`, `--field key=value`) |
| `create` | Create a work item (`--type`, `--title`, `--state`, `--parent`, `--field key=value`) |

### Comment
| Command | Description |
|---------|-------------|
| `list <id>` | List comments on a work item |
| `add <id> <text>` | Add a comment to a work item |

### Query
| Command | Description |
|---------|-------------|
| `mine` | Get active work items assigned to current user |
| `run <wiql>` | Execute a raw WIQL query |

## Common Examples

```bash
# Get a specific work item as JSON
cli-anything-azdo --json workitem show 12345

# List active bugs assigned to me
cli-anything-azdo --json workitem list --state Active --type Bug --assigned-to @Me

# Search for items by title
cli-anything-azdo --json workitem search "login"

# Get my active work items
cli-anything-azdo --json query mine

# Run a custom WIQL query
cli-anything-azdo --json query run "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.State] = 'Active' AND [System.WorkItemType] = 'Bug'"

# List comments on a work item
cli-anything-azdo --json comment list 12345

# Add a comment
cli-anything-azdo comment add 12345 "Work completed"

# Create a child task
cli-anything-azdo --json workitem create --type Task --title "Implement feature" --parent 12345

# Update work item state
cli-anything-azdo workitem update 12345 --state Done
```

## For AI Agents

1. **Always use `--json` flag** for parseable output
2. **Set defaults first** to avoid passing IDs on every call:
   `auth set-defaults --org AMDigitalTech --project Technology --tenant your-tenant.onmicrosoft.com`
3. **Check return codes** — 0 for success, non-zero for errors
4. **Use env vars** for CI: `AZDO_ORG`, `AZDO_PROJECT`, `AZDO_TENANT`, `AZDO_PAT`
5. **`query mine`** is the fastest way to get current user's active items
6. **`workitem show <id>`** returns full details including parent/child relations

## Version

1.0.0
