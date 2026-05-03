#!/usr/bin/env bash
# ralph — Autonomous coding agent loop runner
#
# Usage: ralph [options] [-- arg1 arg2 ...]
# See ralph --help for full usage.

set -euo pipefail

# Resolve RALPH_DIR to the directory containing this script (following symlinks)
RALPH_SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$RALPH_SOURCE" ]]; do
    RALPH_DIR="$(cd -P "$(dirname "$RALPH_SOURCE")" && pwd)"
    RALPH_SOURCE="$(readlink "$RALPH_SOURCE")"
    [[ "$RALPH_SOURCE" != /* ]] && RALPH_SOURCE="$RALPH_DIR/$RALPH_SOURCE"
done
RALPH_DIR="$(cd -P "$(dirname "$RALPH_SOURCE")" && pwd)"
export RALPH_DIR

# Source library files
source "$RALPH_DIR/lib/harness-pi.sh"
source "$RALPH_DIR/lib/harness-claude.sh"
source "$RALPH_DIR/lib/core.sh"

# --- Subcommands ---
case "${1:-}" in
    pause)
        touch .ralph-pause
        echo "Ralph will pause after the current iteration."
        exit 0
        ;;
    stop)
        touch .ralph-stop
        echo "Ralph will stop after the current iteration."
        exit 0
        ;;
esac

# --- Defaults ---
RALPH_MODE="taskfile"
RALPH_STEPS=(implement review)
RALPH_ITERATIONS=10
RALPH_HARNESS="pi"
RALPH_VERBOSE=false
RALPH_INTERACTIVE=false
RALPH_PAUSE=false
RALPH_CLAUDE_MODE="windows"
RALPH_TARGET=""

# --- Parse flags ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            cat <<'HELP'
ralph — Autonomous coding agent loop runner

Usage: ralph [options] <target>
       ralph pause          Pause after the current iteration
       ralph stop           Stop after the current iteration

Target:
  A project directory path (taskfile mode) or work item reference like AB#12345 (azdo mode).

Options:
  -m, --mode <mode>        Task mode: taskfile, azdo (default: taskfile, auto-detects azdo from AB#nnn)
  -s, --steps <agents>     Comma-separated agent steps per iteration (default: implement,review)
  -n <count>               Max iterations (default: 10, implies -i when 1)
  -i                       Interactive mode (single iteration, no headless flag)
  --harness <pi|claude>    AI harness to use (default: pi)
  -l                       Use native Linux claude binary (only with --harness claude)
  -v, --verbose            Show all tool calls
  --pause                  Prompt before each iteration
  -h, --help               Show this help

Agent Steps:
  implement                Pick a task, implement it, commit (default)
  plan                     Review work, break into tasks, update plan
  review                   Review recent changes for quality
  test                     Write/run tests for recent changes

Prompt Resolution:
  Agent prompts:  ~/.ralph/agents/<name>.md  →  <ralph>/prompts/agents/<name>.md
  Mode prompts:   ~/.ralph/modes/<name>.md   →  <ralph>/prompts/modes/<name>.md

Examples:
  ralph /path/to/project                               # taskfile mode, implement + review
  ralph -m azdo AB#12345                                # azdo mode
  ralph AB#12345                                        # auto-detects azdo mode
  ralph -s plan,implement,review,test /path/to/project  # custom pipeline
  ralph --harness claude /path/to/project               # use Claude Code
  ralph -n 1 /path/to/project                           # single interactive iteration
  ralph -v /path/to/project                             # verbose output
HELP
            exit 0
            ;;
        -m|--mode)
            RALPH_MODE="$2"
            shift 2
            ;;
        -s|--steps)
            IFS=',' read -ra RALPH_STEPS <<< "$2"
            shift 2
            ;;
        -n)
            RALPH_ITERATIONS="$2"
            shift 2
            ;;
        -i)
            RALPH_INTERACTIVE=true
            shift
            ;;
        -v|--verbose)
            RALPH_VERBOSE=true
            shift
            ;;
        -l)
            RALPH_CLAUDE_MODE="native"
            shift
            ;;
        --harness)
            RALPH_HARNESS="$2"
            shift 2
            ;;
        --pause)
            RALPH_PAUSE=true
            shift
            ;;
        --)
            shift
            RALPH_TARGET="${1:-}"
            break
            ;;
        *)
            RALPH_TARGET="$1"
            shift
            ;;
    esac
done

# -n 1 implies interactive; -i implies single iteration
if [[ "$RALPH_ITERATIONS" -eq 1 ]]; then
    RALPH_INTERACTIVE=true
fi
if [[ "$RALPH_INTERACTIVE" == true ]]; then
    RALPH_ITERATIONS=1
fi

# Export for harness adapters
export RALPH_VERBOSE RALPH_INTERACTIVE RALPH_CLAUDE_MODE

# Run
_ralph_run_loop
