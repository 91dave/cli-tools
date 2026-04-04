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

### IcePanel

**Prerequisites:** Python 3.10+, an IcePanel account with an API key ([generate one here](https://app.icepanel.io/settings/api-keys))

```bash
# Install
pip install "cli-anything-icepanel @ git+https://github.com/91dave/cli-tools.git#subdirectory=icepanel"

# Set up authentication
cli-anything-icepanel auth login

# List your organizations
cli-anything-icepanel org list

# Explore model objects
cli-anything-icepanel object list
```

**Upgrading:**

```bash
pip install --upgrade --force-reinstall "cli-anything-icepanel @ git+https://github.com/91dave/cli-tools.git#subdirectory=icepanel"
```

### Azure DevOps

**Prerequisites:** Python 3.10+, [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed and logged in (`az login --tenant <TENANT>`)

```bash
# Install
pip install "cli-anything-azdo @ git+https://github.com/91dave/cli-tools.git#subdirectory=azdo"

# Configure defaults
cli-anything-azdo auth set-defaults --org <ORG> --project <PROJECT> --tenant <TENANT>

# Check authentication
cli-anything-azdo auth status

# Show a work item
cli-anything-azdo workitem show 12345

# List child work items
cli-anything-azdo workitem children 12345

# Inspect all fields (including custom fields)
cli-anything-azdo workitem fields 12345

# Search by title
cli-anything-azdo workitem search "search text"

# List and add comments
cli-anything-azdo comment list 12345
cli-anything-azdo comment add 12345 "A comment"

# Interactive REPL
cli-anything-azdo
```

**Upgrading:**

```bash
pip install --upgrade --force-reinstall "cli-anything-azdo @ git+https://github.com/91dave/cli-tools.git#subdirectory=azdo"
```

## Adding a New CLI

See [CONTRIBUTING.md](CONTRIBUTING.md).
