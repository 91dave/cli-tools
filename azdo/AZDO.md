# cli-anything-azdo

Azure DevOps CLI — Work items, queries, and comments from the command line.

Part of the [cli-anything](https://github.com/HKUDS/CLI-Anything) toolkit.

---

## Authentication

### Prerequisites

1. **Azure CLI** installed — [Install guide](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
2. **Logged in** to the correct tenant:

```bash
az login --tenant your-tenant.onmicrosoft.com
```

### How It Works

The CLI acquires a short-lived Bearer token using:

```bash
az account get-access-token \
  --resource 499b84ac-1321-427f-aa17-267ca6975798 \
  --tenant your-tenant.onmicrosoft.com
```

- **Resource ID** `499b84ac-1321-427f-aa17-267ca6975798` is the Azure DevOps API resource
- The token is fetched on each request — no secrets are stored
- The token is valid for ~1 hour; `az login` refreshes automatically when possible

### PAT Fallback

If `az` CLI is unavailable, set a Personal Access Token:

```bash
export AZDO_PAT="your-personal-access-token"
```

This uses Basic auth (`:<PAT>` base64-encoded).

### Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `az: command not found` | Azure CLI not installed | Install from link above |
| `AADSTS700016: Application not found` | Wrong tenant | Run `az login --tenant your-tenant.onmicrosoft.com` |
| `Token expired` / `401 Unauthorized` | Cached token expired | Run `az login` again |
| `Identity not materialized` | User exists in AAD but not Azure DevOps | Ask an admin to add you to the Azure DevOps org |
| `TF400813: Resource not available` | Wrong org or project name | Check `auth set-defaults` values |

---

## Installation

### From the repo (development)

```bash
cd azdo
pip install -e ".[dev]"
```

### Direct install

```bash
pip install "cli-anything-azdo @ git+https://github.com/91dave/cli-tools.git#subdirectory=azdo"
```

---

## Configuration

Set default org, project, and tenant so you don't need to specify them on every call:

```bash
cli-anything-azdo auth set-defaults \
  --org AMDigitalTech \
  --project Technology \
  --tenant your-tenant.onmicrosoft.com
```

Config is stored at `~/.cli-anything-azdo/config.json` with `0600` permissions.

---

## Commands

### Auth

```bash
# Check connection status
cli-anything-azdo auth status

# Set defaults
cli-anything-azdo auth set-defaults --org AMDigitalTech --project Technology --tenant your-tenant.onmicrosoft.com
```

### Work Items

```bash
# Show a single work item
cli-anything-azdo workitem show 12345

# List with filters
cli-anything-azdo workitem list --state Active --assigned-to @Me
cli-anything-azdo workitem list --type Bug --top 10

# Search by title
cli-anything-azdo workitem search "login issue"

# Show child items
cli-anything-azdo workitem children 12345

# Update fields
cli-anything-azdo workitem update 12345 --state Done
cli-anything-azdo workitem update 12345 --field "System.Description=Updated description"

# Create a new work item
cli-anything-azdo workitem create --type Task --title "New task" --parent 12345
```

### Comments

```bash
# List comments
cli-anything-azdo comment list 12345

# Add a comment
cli-anything-azdo comment add 12345 "This is done"
```

### Queries (WIQL)

```bash
# Get my active items
cli-anything-azdo query mine

# Run raw WIQL
cli-anything-azdo query run "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.State] = 'Active'"
```

### JSON Output

Add `--json` before any subcommand for structured JSON output:

```bash
cli-anything-azdo --json workitem show 12345
cli-anything-azdo --json query mine
```

### Interactive REPL

Run without a subcommand to enter the interactive REPL:

```bash
cli-anything-azdo
```

The REPL checks authentication on startup, provides command history, and supports all commands.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZDO_ORG` | Organization name | From config |
| `AZDO_PROJECT` | Project name | From config |
| `AZDO_TENANT` | Azure AD tenant | From config |
| `AZDO_PAT` | Personal Access Token (fallback auth) | None |

---

## For AI Agents

1. **Always use `--json`** for parseable structured output
2. **Set defaults first** to avoid passing org/project/tenant on every call
3. **Check return codes** — 0 for success, non-zero for errors
4. **`query mine`** is the fastest way to get the current user's active work items
5. **`workitem show <id>`** returns full details including parent/child relations
6. **Use env vars** in CI: `AZDO_ORG`, `AZDO_PROJECT`, `AZDO_TENANT`, `AZDO_PAT`

---

## Running Tests

```bash
cd azdo
pip install -e ".[dev]"

# Unit tests (mocked, no network)
pytest

# Integration tests (requires az login)
pytest -m integration
```
