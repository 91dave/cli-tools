# cli-tools

CLI tools for internal platforms and third-party services, built with the
[CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology.

## Available CLIs

| CLI | Install | Description |
|-----|---------|-------------|
| `cli-anything-icepanel` | `pip install "cli-anything-icepanel @ git+https://github.com/91dave/cli-tools.git#subdirectory=icepanel"` | IcePanel architecture visualization |
| `cli-anything-azdo` | `pip install "cli-anything-azdo @ git+https://github.com/91dave/cli-tools.git#subdirectory=azdo"` | Azure DevOps work items, queries, and comments |

## Quick Start

Install any CLI directly from this repo:

```bash
pip install "cli-anything-icepanel @ git+https://github.com/91dave/cli-tools.git#subdirectory=icepanel"
```

Or for development:

```bash
git clone https://github.com/91dave/cli-tools.git
cd cli-tools/icepanel
pip install -e ".[dev]"
```

### Prerequisites

- Python 3.10+
- An IcePanel account with an API key ([generate one here](https://app.icepanel.io/settings/api-keys))

### After Install

```bash
# Set up authentication
cli-anything-icepanel auth login

# List your organizations
cli-anything-icepanel org list

# Explore model objects
cli-anything-icepanel object list
```

### Upgrading

```bash
pip install --upgrade --force-reinstall "cli-anything-icepanel @ git+https://github.com/91dave/cli-tools.git#subdirectory=icepanel"
```

## Adding a New CLI

See [CONTRIBUTING.md](CONTRIBUTING.md).
