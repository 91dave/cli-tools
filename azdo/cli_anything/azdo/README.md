# cli-anything-azdo

Azure DevOps work item CLI — part of the cli-anything toolkit.

## Prerequisites

1. **Azure CLI** installed: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
2. **Logged in**: `az login --tenant adammatthewdigital.onmicrosoft.com`

## Installation

```bash
cd azdo
pip install -e ".[dev]"
```

## Quick Start

```bash
# Configure defaults
cli-anything-azdo auth set-defaults \
  --org AMDigitalTech \
  --project Technology \
  --tenant adammatthewdigital.onmicrosoft.com

# Check auth status
cli-anything-azdo auth status

# JSON output for agents
cli-anything-azdo --json auth status
```

## Authentication

Token is acquired automatically via:
```bash
az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --tenant adammatthewdigital.onmicrosoft.com
```

**PAT fallback**: Set `AZDO_PAT` environment variable to use a Personal Access Token instead.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZDO_ORG` | Organization name | From config |
| `AZDO_PROJECT` | Project name | From config |
| `AZDO_TENANT` | Azure AD tenant | From config |
| `AZDO_PAT` | Personal Access Token (fallback) | None |

## Command Groups

| Group | Commands | Description |
|-------|----------|-------------|
| `auth` | `status`, `set-defaults` | Authentication and configuration |
| `workitem` | `show`, `list`, `search`, `children`, `update`, `create` | Work item operations |
| `comment` | `list`, `add` | Work item comments |
| `query` | `run`, `mine` | WIQL query operations |

## Running Tests

```bash
# Unit tests (mocked, no network)
pytest

# Integration tests (requires az login)
pytest -m integration
```
