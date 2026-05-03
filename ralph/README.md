# Ralph — Autonomous Coding Agent Loop Runner

An autonomous loop runner that iterates an AI coding agent over a set of tasks until all work is complete or an error is encountered. Supports configurable agent pipelines, task-tracking modes, and multiple AI harnesses.

## Installation

```bash
ln -sf /path/to/cli-tools/ralph/ralph.sh ~/.local/bin/ralph
```

## Usage

```bash
ralph [options] <target>
ralph pause          # Pause after the current iteration
ralph stop           # Stop after the current iteration
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `-m, --mode <mode>` | Task mode: `taskfile`, `azdo` (auto-detects `azdo` from `AB#nnn`) | `taskfile` |
| `-s, --steps <agents>` | Comma-separated agent steps per iteration | `implement,review` |
| `-n <count>` | Max iterations (implies `-i` when `1`) | `10` |
| `-i` | Interactive mode (single iteration, no headless flag) | Off |
| `--harness <pi\|claude>` | AI harness to use | `pi` |
| `-l` | Use native Linux `claude` binary (only with `--harness claude`) | Windows mode |
| `-v, --verbose` | Show all tool calls | Off |
| `--pause` | Prompt before each iteration | Off |

## Concepts

### Modes (how tasks are tracked)

A **mode** defines how tasks are discovered, claimed, updated, and completed.

| Mode | Description |
|------|-------------|
| `taskfile` | `task-*.md` files + `progress.md` + `PLAN.md` in a project directory |
| `azdo` | Azure DevOps work items (parent + children) |

### Agents (what to do in each step)

An **agent** defines a role for one step of an iteration.

| Agent | Purpose |
|-------|---------|
| `implement` | Pick a task, implement it, commit |
| `plan` | Review work, break into tasks, update the plan |
| `review` | Review recent changes for quality, fix or flag issues |
| `test` | Write/run tests for recent changes, report gaps |

### Steps Pipeline

Each iteration runs a configurable sequence of agents. The default is `implement` only.

```bash
ralph -s plan,implement,review,test /path/to/project
```

Each step gets a combined prompt: the agent prompt + the mode prompt, with named placeholders (`{{project}}`, `{{workitem}}`, `{{agent}}`, `{{context}}`) substituted from the target arg and pipeline state.

### Harnesses (which AI tool runs it)

| Harness | Binary | Output format |
|---------|--------|---------------|
| `pi` | `pi` | `--mode json` |
| `claude` | `claude.exe` / `claude` | `--output-format stream-json` |

## Prompt Resolution

Prompts are resolved with user overrides taking precedence:

1. `~/.ralph/agents/<name>.md` or `~/.ralph/modes/<name>.md` (user override)
2. `<ralph>/prompts/agents/<name>.md` or `<ralph>/prompts/modes/<name>.md` (default)

This allows customising agent behaviour or mode instructions without modifying the repo.

## Controlling a Running Loop

From another terminal in the same working directory:

| Command | Effect |
|---------|--------|
| `ralph pause` | Pause after the current iteration (prompts to continue) |
| `ralph stop` | Stop after the current iteration |

## Progress Output

In headless mode, ralph streams filtered progress. Each line is prefixed with elapsed time:

```
[+ 0m05s]   ▶ Bash: git status
[+ 0m12s]   ◇ Updating the configuration file...
[+ 1m30s]   ✓ Done: 8 turns, $0.42, 90s
```

| Symbol | Meaning |
|--------|---------|
| ▶ | Tool call |
| ◇ | Assistant text |
| ✓ | Iteration summary |
| ⏳ | API retry |

Use `-v` to show all tool calls (default hides low-noise tools like read, grep, find).

## Examples

```bash
# Task-file workflow (up to 10 iterations)
ralph /path/to/project

# Azure DevOps work item (auto-detected)
ralph AB#12345

# Custom pipeline
ralph -s plan,implement,review,test /path/to/project

# Use Claude Code instead of pi
ralph --harness claude /path/to/project

# Single interactive iteration
ralph -n 1 /path/to/project

# Verbose output with pause between iterations
ralph -v --pause -n 5 /path/to/project
```
