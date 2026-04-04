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
