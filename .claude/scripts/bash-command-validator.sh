#!/bin/bash
# PreToolUse hook: Validates bash commands before execution
# Reads JSON from stdin with tool_name and tool_input

set -e

# Read JSON input from stdin
input=$(cat)

# Extract tool info
tool_name=$(echo "$input" | jq -r '.tool_name // empty' 2>/dev/null)
command=$(echo "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Debug logging
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Hook fired - tool: $tool_name, command: $command" >> ~/.claude-hook-debug.log

# Only process Bash tool calls
if [[ "$tool_name" != "Bash" ]]; then
    exit 0
fi

# Validation Rule 1: Check for untracked files before git push
if [[ "$command" =~ ^git\ push ]]; then
    echo "🔍 Checking for untracked code files..." >&2

    untracked=$(git status --porcelain 2>/dev/null | grep '^??' | grep -E '\.(py|tsx?|js)$')

    if [ -n "$untracked" ]; then
        echo "⚠️  UNTRACKED CODE FILES DETECTED:" >&2
        echo "$untracked" >&2
        echo "" >&2
        echo "Verify these are not needed before pushing." >&2
    else
        echo "✅ No untracked code files" >&2
    fi

    exit 0  # Allow push (just warn)
fi

# Validation Rule 2: Run smoke tests before git commit
if [[ "$command" =~ ^git\ commit ]]; then
    echo "🔥 Running smoke tests before commit..." >&2

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    BACKEND_DIR="$PROJECT_ROOT/backend"

    # Change to backend directory
    cd "$BACKEND_DIR"

    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    # Run smoke tests
    if python -m pytest tests/smoke/ -x -q --tb=short 2>&1 | tee /tmp/smoke-test-output.log >&2; then
        echo "✅ Smoke tests passed!" >&2
        exit 0  # Allow commit
    else
        echo "❌ Smoke tests failed! Fix errors before committing." >&2
        echo "" >&2
        echo "See full output above." >&2
        exit 2  # Block commit
    fi
fi

# Allow all other bash commands
exit 0
