#!/usr/bin/env bash
# core.sh — Core loop and prompt logic for ralph
# Sourced by ralph.sh — not executable standalone.

# Resolve a prompt file: user override (~/.ralph/<type>/<name>.md) or default.
# Args: $1 = type (agents|modes), $2 = name
# Prints the resolved file path, or empty string if not found.
_ralph_resolve_prompt() {
    local type="$1"
    local name="$2"
    local user_path="$HOME/.ralph/${type}/${name}.md"
    local default_path="${RALPH_DIR}/prompts/${type}/${name}.md"

    if [[ -f "$user_path" ]]; then
        echo "$user_path"
    elif [[ -f "$default_path" ]]; then
        echo "$default_path"
    else
        echo ""
    fi
}

# Compose a prompt from agent + mode, substituting named placeholders.
# Args: $1 = agent name, $2 = mode name, $3 = mode arg (project path or work item)
# Prints the composed prompt to stdout.
_ralph_compose_prompt() {
    local agent_name="$1"
    local mode_name="$2"
    local mode_arg="${3:-}"

    local agent_file mode_file
    agent_file=$(_ralph_resolve_prompt "agents" "$agent_name")
    mode_file=$(_ralph_resolve_prompt "modes" "$mode_name")

    if [[ -z "$agent_file" ]]; then
        echo "ERROR: Agent prompt not found: $agent_name" >&2
        return 1
    fi
    if [[ -z "$mode_file" ]]; then
        echo "ERROR: Mode prompt not found: $mode_name" >&2
        return 1
    fi

    local prompt
    prompt="$(cat "$agent_file")"$'\n\n'"$(cat "$mode_file")"

    # Substitute named placeholders
    prompt="${prompt//\{\{agent\}\}/$agent_name}"

    # Mode-specific arg placeholder
    case "$mode_name" in
        taskfile) prompt="${prompt//\{\{project\}\}/$mode_arg}" ;;
        azdo)    prompt="${prompt//\{\{workitem\}\}/$mode_arg}" ;;
    esac

    # Inject step context from previous steps
    local step_context=""
    if [[ -f .ralph-step-context ]]; then
        step_context=$'\n## Context from Previous Steps\n'"$(cat .ralph-step-context)"
    fi
    prompt="${prompt//\{\{context\}\}/$step_context}"

    echo "$prompt"
}

# Check result text for status signals.
# Args: $1 = result text
# Returns: 0 = COMPLETE, 1 = ERROR, 2 = continue
_ralph_check_status() {
    local result_text="$1"

    if echo "$result_text" | grep -q '<status>COMPLETE</status>' 2>/dev/null; then
        return 0
    fi

    if echo "$result_text" | grep -q '<status>ERROR' 2>/dev/null; then
        RALPH_ERROR_MSG=$(echo "$result_text" | grep -o '<status>ERROR[^<]*</status>' | head -1 | sed 's/<[^>]*>//g')
        return 1
    fi

    return 2
}

# Run the main ralph loop.
# Uses globals: RALPH_MODE, RALPH_STEPS[], RALPH_ITERATIONS, RALPH_HARNESS,
#               RALPH_VERBOSE, RALPH_INTERACTIVE, RALPH_PAUSE, RALPH_TARGET,
#               RALPH_CLAUDE_MODE, RALPH_DIR
_ralph_run_loop() {
    # Auto-detect azdo mode from AB#nnn pattern
    if [[ "$RALPH_MODE" == "taskfile" && -n "$RALPH_TARGET" && "$RALPH_TARGET" =~ ^AB#[0-9]+ ]]; then
        RALPH_MODE="azdo"
    fi

    # Ensure progress.md exists for taskfile mode
    if [[ "$RALPH_MODE" == "taskfile" && -n "$RALPH_TARGET" && -d "$RALPH_TARGET" && ! -f "$RALPH_TARGET/progress.md" ]]; then
        touch "$RALPH_TARGET/progress.md"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Created $RALPH_TARGET/progress.md"
    fi

    # Clean up any stale signal files
    rm -f .ralph-pause .ralph-stop

    local tmpfile
    tmpfile=$(mktemp)
    trap "rm -f '$tmpfile' .ralph-pause .ralph-stop .ralph-step-context" RETURN

    # Select harness run function
    local run_fn
    case "$RALPH_HARNESS" in
        pi)    run_fn="_ralph_run_pi" ;;
        claude) run_fn="_ralph_run_claude" ;;
        *)
            echo "ERROR: Unknown harness: $RALPH_HARNESS" >&2
            return 1
            ;;
    esac

    for ((i = 1; i <= RALPH_ITERATIONS; i++)); do
        # Check for signal files between iterations
        if [[ -f .ralph-stop ]]; then
            rm -f .ralph-stop
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Stopped by signal before iteration $i."
            return 0
        fi
        if [[ -f .ralph-pause ]]; then
            rm -f .ralph-pause
            RALPH_PAUSE=true
        fi

        if [[ "$RALPH_PAUSE" == true && $i -gt 1 ]]; then
            read -rp "Continue to iteration $i/$RALPH_ITERATIONS? [Y/n] " answer
            if [[ "$answer" =~ ^[Nn] ]]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] Stopped by user before iteration $i."
                return 0
            fi
        fi

        echo "[$(date '+%Y-%m-%d %H:%M:%S')] --- Iteration $i of $RALPH_ITERATIONS ---"

        # Clean step context at the start of each iteration
        rm -f .ralph-step-context

        # Run each step in the pipeline
        for step in "${RALPH_STEPS[@]}"; do
            if [[ ${#RALPH_STEPS[@]} -gt 1 ]]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')]   Step: $step"
            fi

            local prompt
            prompt=$(_ralph_compose_prompt "$step" "$RALPH_MODE" "$RALPH_TARGET")
            if [[ $? -ne 0 ]]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] $prompt"
                return 1
            fi

            local iter_start
            iter_start=$(date +%s)

            RALPH_RESULT_TEXT=""
            $run_fn "$prompt" "$tmpfile" "$iter_start" "$step"

            if [[ "$RALPH_INTERACTIVE" == true ]]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] Interactive session ended."
                return 0
            fi

            _ralph_check_status "$RALPH_RESULT_TEXT"
            local status=$?

            if [[ $status -eq 0 ]]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] Plan completed, exiting."
                return 0
            elif [[ $status -eq 1 ]]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] $RALPH_ERROR_MSG"
                return 1
            fi
            # status 2 = continue to next step/iteration
        done
    done

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Reached max iterations ($RALPH_ITERATIONS) without completion."
    return 1
}
