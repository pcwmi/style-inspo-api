#!/bin/bash
# Check for untracked code files before git push
# Warns about .py, .ts, .tsx, .js files that might be missing from commit

untracked=$(git status --porcelain | grep '^??' | grep -E '\.(py|tsx?|js)$')

if [ -n "$untracked" ]; then
    echo "⚠️  UNTRACKED CODE FILES DETECTED:"
    echo "$untracked"
    echo ""
    echo "Verify these are not needed before pushing."
fi
