---
name: >-
  cli-anything-icepanel
description: >-
  Command-line interface for IcePanel — manage architecture landscapes, model objects, connections, diagrams, flows, versions, tags, domains, and teams via the IcePanel REST API.
---

# cli-anything-icepanel

CLI harness for **IcePanel** — architecture visualization and C4 modelling from the command line.

## Installation

```bash
pip install -e .   # from icepanel/agent-harness/
```

**Prerequisites:**
- Python 3.10+
- IcePanel API key (generate at https://app.icepanel.io → Org Settings → API Keys)

## Usage

```bash
# Setup
cli-anything-icepanel auth setup --api-key "keyId:keySecret"
cli-anything-icepanel auth set-defaults --org-id <ID> --landscape-id <ID>

# JSON output for agents
cli-anything-icepanel --json object list
cli-anything-icepanel --json flow export-mermaid <flowId>

# Interactive REPL
cli-anything-icepanel
```

## Command Groups

### Auth
| Command | Description |
|---------|-------------|
| `setup` | Configure API key and defaults |
| `set-defaults` | Set default org/landscape/version IDs |
| `status` | Check authentication status |
| `logout` | Remove saved config |

### Org
| Command | Description |
|---------|-------------|
| `list` | List organizations |
| `info` | Get organization details |
| `landscapes` | List landscapes in an org |
| `create-landscape` | Create a new landscape |
| `users` | List organization users |
| `invite` | Invite a user |

### Landscape
| Command | Description |
|---------|-------------|
| `info` | Get landscape details |
| `update` | Update landscape properties |
| `delete` | Delete a landscape |
| `duplicate` | Duplicate a landscape |
| `export` | Start async export |
| `export-status` | Check export status |
| `search` | Search within landscape |

### Version
| Command | Description |
|---------|-------------|
| `list` | List versions |
| `create` | Create a version snapshot |
| `info` | Get version details |
| `delete` | Delete a version |

### Object
| Command | Description |
|---------|-------------|
| `list` | List model objects |
| `create` | Create (system, app, store, actor, component, group) |
| `info` | Get object details |
| `update` | Update an object |
| `delete` | Delete (cascades to children) |
| `dependencies` | Export dependencies JSON |
| `export-csv` | Export all objects as CSV |

### Connection
| Command | Description |
|---------|-------------|
| `list` | List connections |
| `create` | Create connection between objects |
| `info` | Get connection details |
| `update` | Update a connection |
| `delete` | Delete a connection |
| `generate-description` | AI-generate description |
| `export-csv` | Export all as CSV |

### Diagram
| Command | Description |
|---------|-------------|
| `list` | List diagrams |
| `info` | Get diagram details |
| `delete` | Delete a diagram |
| `content` | Get diagram content |
| `export-image` | Start image export |

### Flow
| Command | Description |
|---------|-------------|
| `list` | List flows |
| `info` | Get flow details |
| `delete` | Delete a flow |
| `export-mermaid` | Export as Mermaid syntax |
| `export-text` | Export as plain text |
| `export-code` | Export as code |

### Tag
| Command | Description |
|---------|-------------|
| `list` | List tags |
| `info` | Get tag details |
| `groups` | List tag groups |

### Domain
| Command | Description |
|---------|-------------|
| `list` | List domains |
| `info` | Get domain details |

### Team
| Command | Description |
|---------|-------------|
| `list` | List teams |
| `info` | Get team details |
| `create` | Create a team |
| `delete` | Delete a team |

## For AI Agents

1. **Always use `--json` flag** for parseable output
2. **Set defaults first** to avoid passing IDs on every call:
   `auth set-defaults --org-id <ID> --landscape-id <ID>`
3. **Check return codes** — 0 for success, non-zero for errors
4. **Use env vars** for CI: `ICEPANEL_API_KEY`, `ICEPANEL_ORG_ID`, `ICEPANEL_LANDSCAPE_ID`

## Version

1.0.0
