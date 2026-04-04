# Contributing — Adding a New CLI

This repo follows the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology.
Each CLI lives in its own top-level directory with a self-contained `setup.py`.

## Steps to Add a New CLI

### 1. Create the directory structure

```
<tool>/
├── setup.py
├── <TOOL>.md                    # Tool-specific documentation
└── cli_anything/                # NO __init__.py here (PEP 420 namespace package)
    └── <tool>/
        ├── __init__.py
        ├── __main__.py
        ├── <tool>_cli.py        # Click CLI entry point
        ├── README.md            # LLM-facing tool description
        ├── core/                # Command implementations
        │   ├── __init__.py
        │   └── ...
        ├── utils/               # Shared utilities
        │   ├── __init__.py
        │   ├── <tool>_backend.py
        │   └── repl_skin.py     # Copy from an existing CLI
        ├── skills/              # Agent skill definitions
        │   └── SKILL.md
        └── tests/
            ├── __init__.py
            └── test_core.py
```

### 2. Create `setup.py`

Use `name="cli-anything-<tool>"` and `find_namespace_packages(include=["cli_anything.*"])`.

```python
from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-<tool>",
    version="1.0.0",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.28.0",
        "prompt-toolkit>=3.0.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0.0", "pytest-cov>=4.0.0"],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-<tool>=cli_anything.<tool>.<tool>_cli:main",
        ],
    },
    zip_safe=False,
)
```

### 3. Important: Namespace package rules

- The `cli_anything/` directory must **NOT** contain an `__init__.py` file
- This is a PEP 420 implicit namespace package — it allows multiple CLIs to coexist under `cli_anything.*`
- Each `cli_anything/<tool>/` directory **does** have an `__init__.py`

### 4. Update the root README

Add your CLI to the table in `README.md`:

```markdown
| `cli-anything-<tool>` | `pip install "cli-anything-<tool> @ git+https://github.com/91dave/cli-tools.git#subdirectory=<tool>"` | Description |
```

### 5. Test

```bash
cd <tool>
pip install -e ".[dev]"
pytest
cli-anything-<tool> --help
```

### 6. Windows compatibility

These CLIs must work on both Unix and Windows. Avoid Unix-only modules at the
top level — in particular **do not** `import fcntl` unconditionally. For file
locking, use a platform check:

```python
import sys

if sys.platform == "win32":
    import msvcrt
    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
else:
    import fcntl
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
```

### 7. Commit

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add <tool> CLI
```
