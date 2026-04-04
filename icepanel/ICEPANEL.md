# IcePanel CLI — Architecture & Analysis

## Phase 1: Analysis

### Backend Engine
IcePanel is a SaaS application with a REST API at `https://api.icepanel.io/v1`.
No local software to invoke — the "backend" is the remote API.

### Authentication
- API key in format `keyId:keySecret`
- Header: `Authorization: ApiKey <keyId>:<keySecret>`
- Keys generated at: Organization Settings → API Keys

### Data Model (from OpenAPI spec)
- **Organization** → top-level container
- **Landscape** → architecture workspace (belongs to an org)
- **Version** → snapshot of a landscape ("latest" = current)
- **Model Object** → systems, apps, stores, actors, components, groups (nested)
- **Model Connection** → relationships between objects (origin → target)
- **Diagram** → visual layout of objects, with content and image export
- **Flow** → sequence diagram (steps between objects), exportable as Mermaid/text/code
- **Tag / Tag Group** → categorization
- **Domain** → business capability grouping
- **Team** → ownership / permissions
- **Draft** → change proposals (not yet in CLI)
- **Comment** → discussion threads (not yet in CLI)
- **Share Link** → external sharing (not yet in CLI)

### API Endpoints (120+ from OpenAPI)
Full endpoint catalog extracted from the published OpenAPI spec at
`https://developer.icepanel.io/api-reference/openapi.json`.

## Phase 2: Design

### Command Groups
| Group | API Resource |
|-------|-------------|
| `auth` | Local config (API key, defaults) |
| `org` | `/organizations` |
| `landscape` | `/landscapes/{id}` |
| `version` | `/landscapes/{id}/versions` |
| `object` | `.../model/objects` |
| `connection` | `.../model/connections` |
| `diagram` | `.../diagrams` |
| `flow` | `.../flows` |
| `tag` | `.../tags` + `.../tag-groups` |
| `domain` | `.../domains` |
| `team` | `/organizations/{id}/teams` |

### State Model
- Persistent config at `~/.cli-anything-icepanel/config.json`
- Stores: api_key, default organization_id, landscape_id, version_id
- Env vars override config (ICEPANEL_API_KEY, ICEPANEL_ORG_ID, etc.)
- No local project files — all state is in the IcePanel API

### Output Format
- `--json` flag for machine-readable JSON
- Human-readable key-value pairs by default
- REPL as default when invoked with no subcommand
