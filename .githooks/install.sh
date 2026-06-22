#!/usr/bin/env bash
# Activate the versioned git hooks for this repo (one-time, per clone).
set -e
root="$(git rev-parse --show-toplevel)"
git -C "$root" config core.hooksPath .githooks
chmod +x "$root/.githooks/pre-push"
echo "Installed: core.hooksPath -> .githooks"
echo "The pre-push eval gate is now active."
echo "  bypass once : git push --no-verify"
echo "  skip suite  : SKIP_EVAL_GATE=1 git push"
