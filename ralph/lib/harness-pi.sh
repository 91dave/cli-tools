#!/usr/bin/env bash
# harness-pi.sh — pi-coding-agent harness adapter for ralph
# Sourced by ralph.sh — not executable standalone.
#
# Expects: $RALPH_VERBOSE, $RALPH_INTERACTIVE

# --- Progress filter for pi-coding-agent --mode json output ---
# Args: $1 = "true"|"false" (verbose mode), $2 = epoch start time, $3 = step name
_ralph_pi_progress_filter() {
    local filter_verbose="${1:-false}"
    local filter_start="${2:-$(date +%s)}"
    local filter_step="${3:-}"

    jq --unbuffered -j --argjson verbose "$filter_verbose" --argjson start "$filter_start" --arg step "$filter_step" '
        def elapsed:
            ((now | floor) - $start) |
            if . < 0 then . + 1 else . end |
            "[+\(. / 60 | floor | tostring | if length < 2 then " " + . else . end)m\(. % 60 | tostring | if length < 2 then "0" + . else . end)s]";

        def tool_detail:
            if .toolName == "bash" then ": " + (.args.command // "")
            elif .toolName == "read" then ": " + (.args.path // "")
            elif .toolName == "edit" then ": " + (.args.path // "")
            elif .toolName == "write" then ": " + (.args.path // "")
            elif .toolName == "grep" then ": " + (.args.pattern // "")
            elif .toolName == "find" then ": " + (.args.pattern // "")
            else ": " + (.args.path // .args.command // .args.pattern // "")
            end;

        def is_verbose_only:
            .toolName as $n |
            if ($n == "read" or $n == "grep" or $n == "find" or $n == "ls") then true
            elif $n == "bash" then
                (.args.command // "") | test("^(find |ls |cat |head |tail |grep |rg |sleep )")
            else false end;

        def step_prefix:
            if ($step | length) > 0 then "[\($step)]" else "" end;

        if .type == "message_update" then
            .assistantMessageEvent as $e |
            if $e.type == "text_start" then "\(elapsed) \(step_prefix)  ◇ "
            elif $e.type == "text_delta" then $e.delta
            elif $e.type == "text_end" then "\n"
            else empty end
        elif .type == "tool_execution_start" then
            if ($verbose or (is_verbose_only | not)) then
                "\(elapsed) \(step_prefix)  ▶ \(.toolName)\(tool_detail)\n"
            else empty end
        elif .type == "agent_end" then
            (.messages[-1].usage.cost.total // 0) as $cost |
            ([ .messages[] | select(.role == "assistant") ] | length) as $turns |
            "\(elapsed) \(step_prefix)  ✓ Done: \($turns) turns, $\($cost * 100 | round / 100)\n"
        elif .type == "auto_retry_start" then
            "\(elapsed) \(step_prefix)  ⏳ Retry \(.attempt)/\(.maxAttempts) (\(.errorMessage))\n"
        else empty end
    '
}

# Run a prompt through pi-coding-agent.
# Args: $1 = prompt text, $2 = tmpfile for raw output, $3 = epoch start time
# Returns: sets RALPH_RESULT_TEXT with the agent's final text output
_ralph_run_pi() {
    local prompt="$1"
    local tmpfile="$2"
    local iter_start="$3"

    # Extract @file references from prompt into separate args
    # (pi requires @files as separate CLI arguments, not inline in prompt text)
    local pi_file_args=()
    local pi_prompt="$prompt"
    while [[ "$pi_prompt" =~ ^[[:space:]]*(@[^[:space:]]+)(.*) ]]; do
        pi_file_args+=("${BASH_REMATCH[1]}")
        pi_prompt="${BASH_REMATCH[2]}"
    done
    pi_prompt="${pi_prompt#"${pi_prompt%%[![:space:]]*}"}"  # trim leading whitespace

    if [[ "$RALPH_INTERACTIVE" == true ]]; then
        pi "${pi_file_args[@]}" "$pi_prompt"
        RALPH_RESULT_TEXT=""
    else
        pi --mode json --no-session \
            "${pi_file_args[@]}" \
            -p "$pi_prompt" 2>&1 | tee "$tmpfile" | _ralph_pi_progress_filter "$RALPH_VERBOSE" "$iter_start" "$step_name"

        RALPH_RESULT_TEXT=$(jq -r '
            select(.type == "agent_end") |
            [.messages[-1].content[] | select(.type == "text") | .text] | join("")
        ' "$tmpfile" 2>/dev/null)
    fi
}
