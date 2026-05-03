#!/usr/bin/env bash
# harness-claude.sh — Claude Code harness adapter for ralph
# Sourced by ralph.sh — not executable standalone.
#
# Expects: $RALPH_VERBOSE, $RALPH_INTERACTIVE, $RALPH_CLAUDE_MODE

# --- Progress filter for Claude Code stream-json output ---
# Args: $1 = "true"|"false" (verbose mode), $2 = epoch start time, $3 = step name
_ralph_claude_progress_filter() {
    local filter_verbose="${1:-false}"
    local filter_start="${2:-$(date +%s)}"
    local filter_step="${3:-}"

    jq --unbuffered -r --argjson verbose "$filter_verbose" --argjson start "$filter_start" --arg step "$filter_step" '
        def elapsed:
            ((now | floor) - $start) |
            if . < 0 then . + 1 else . end |
            "[+\(. / 60 | floor | tostring | if length < 2 then " " + . else . end)m\(. % 60 | tostring | if length < 2 then "0" + . else . end)s]";

        def is_verbose_only:
            .name as $n |
            if ($n == "Glob" or $n == "Read" or $n == "Grep"
                or $n == "ToolSearch" or $n == "TodoWrite") then true
            elif $n == "Bash" then
                (.input.command // "") | test("^(find |ls |cat |head |tail |grep |rg |sleep )")
            else false end;

        def tool_detail:
            if .name == "Bash" then ": " + (.input.command // "")
            elif .name == "Read" then ": " + (.input.file_path // "")
            elif .name == "Edit" then ": " + (.input.file_path // "")
            elif .name == "Write" then ": " + (.input.file_path // "")
            elif .name == "Grep" then ": " + (.input.pattern // "")
            elif .name == "Glob" then ": " + (.input.pattern // "")
            elif .name == "Agent" then ": " + (.input.description // "")
            else ": " + (.input.description // .input.file_path // "")
            end;

        def step_prefix:
            if ($step | length) > 0 then "[\($step)]" else "" end;

        if .type == "assistant" then
            (.message.content[] |
                if .type == "tool_use" then
                    if ($verbose or (is_verbose_only | not)) then
                        "\(elapsed) \(step_prefix)  \u25b6 \(.name)\(tool_detail)"
                    else empty end
                elif .type == "text" then
                    (.text | select(length > 0)) |
                    "\(elapsed) \(step_prefix)  \u25c7 \(.)"
                else empty end)
        elif .type == "result" then
            "\(elapsed) \(step_prefix)  \u2713 Done: \(.num_turns) turns, $\(.total_cost_usd // 0 | . * 100 | round / 100), \((.duration_ms // 0) / 1000 | round)s"
        elif .type == "system" and .subtype == "api_retry" then
            "\(elapsed) \(step_prefix)  \u23f3 Retry \(.attempt)/\(.max_retries) (\(.error))"
        else empty end
    '
}

# Run a prompt through Claude Code.
# Args: $1 = prompt text, $2 = tmpfile for raw output, $3 = epoch start time, $4 = step name
# Returns: sets RALPH_RESULT_TEXT with the agent's final text output
_ralph_run_claude() {
    local prompt="$1"
    local tmpfile="$2"
    local iter_start="$3"
    local step_name="${4:-}"

    local claude_bin
    local prompt_file
    if [[ "$RALPH_CLAUDE_MODE" == "native" ]]; then
        prompt_file=$(mktemp)
        claude_bin="claude"
    else
        local win_temp
        win_temp=$(wslpath "$(cmd.exe /c "echo %TEMP%" 2>/dev/null | tr -d '\r')" 2>/dev/null || echo "/tmp")
        prompt_file=$(mktemp "$win_temp/ralph-XXXXXX" 2>/dev/null || mktemp)
        claude_bin="claude.exe"
    fi

    printf '%s' "$prompt" > "$prompt_file"

    if [[ "$RALPH_INTERACTIVE" == true ]]; then
        $claude_bin --permission-mode auto \
            --allowedTools "Bash(git commit:*)" \
            < "$prompt_file"
        rm -f "$prompt_file"
        RALPH_RESULT_TEXT=""
    else
        $claude_bin --permission-mode auto \
            --allowedTools "Bash(git commit:*)" \
            --output-format stream-json --verbose \
            -p < "$prompt_file" 2>&1 | tee "$tmpfile" | _ralph_claude_progress_filter "$RALPH_VERBOSE" "$iter_start" "$step_name"

        rm -f "$prompt_file"

        RALPH_RESULT_TEXT=$(jq -r 'select(.type == "result") | .result // ""' "$tmpfile" 2>/dev/null)
    fi
}
