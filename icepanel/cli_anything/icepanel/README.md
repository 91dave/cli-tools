# cli-anything-icepanel

CLI harness for **IcePanel** — manage architecture landscapes, model objects,
connections, diagrams, flows, versions, tags, domains, and teams from the
command line via the IcePanel REST API.

## Prerequisites

- Python 3.10+
- IcePanel account with API key
  - Generate at: https://app.icepanel.io → Organization Settings → API Keys

## Installation

```bash
cd icepanel/agent-harness
pip install -e .
```

Verify:
```bash
which cli-anything-icepanel
cli-anything-icepanel --help
```

## Quick Start

```bash
# 1. Configure your API key
cli-anything-icepanel auth setup --api-key "YOUR_KEY_ID:YOUR_KEY_SECRET"

# 2. Set defaults to avoid repeating IDs
cli-anything-icepanel auth set-defaults --org-id <ORG_ID> --landscape-id <LANDSCAPE_ID>

# 3. Explore your architecture
cli-anything-icepanel org list
cli-anything-icepanel org landscapes
cli-anything-icepanel object list
cli-anything-icepanel connection list
cli-anything-icepanel flow list
cli-anything-icepanel diagram list

# 4. JSON output for agent consumption
cli-anything-icepanel --json object list
cli-anything-icepanel --json flow export-mermaid <FLOW_ID>

# 5. Interactive REPL
cli-anything-icepanel
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ICEPANEL_API_KEY` | API key (overrides config file) |
| `ICEPANEL_ORG_ID` | Default organization ID |
| `ICEPANEL_LANDSCAPE_ID` | Default landscape ID |
| `ICEPANEL_VERSION_ID` | Default version ID |

## Command Groups

| Group | Description |
|-------|-------------|
| `auth` | API key setup, defaults, status |
| `org` | Organization management, list landscapes/users |
| `landscape` | Get/update/delete/duplicate/export/search |
| `version` | Version snapshots and reverts |
| `object` | Model objects (systems, apps, stores, actors) |
| `connection` | Connections between model objects |
| `diagram` | Diagram management and image export |
| `flow` | Flows with Mermaid/text/code export |
| `tag` | Tags and tag groups |
| `domain` | Domains (business capabilities) |
| `team` | Team management |

## Running Tests

```bash
cd icepanel/agent-harness
python3 -m pytest cli_anything/icepanel/tests/ -v

# Force installed mode
CLI_ANYTHING_FORCE_INSTALLED=1 python3 -m pytest cli_anything/icepanel/tests/ -v -s
```
