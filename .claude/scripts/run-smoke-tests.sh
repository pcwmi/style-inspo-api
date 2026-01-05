#!/bin/bash
# Run smoke tests before commit/push
# These tests should complete in <30 seconds

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "🔥 Running smoke tests..."

# Change to backend directory
cd "$BACKEND_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run smoke tests with pytest
# -x: stop on first failure
# -q: quiet output
# --tb=short: short tracebacks
python -m pytest tests/smoke/ -x -q --tb=short

echo "✅ Smoke tests passed!"
