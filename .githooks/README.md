# Git hooks

Versioned hooks for this repo. They live here (not `.git/hooks/`) so they're
shared and reviewable. Activate once per clone:

```bash
./.githooks/install.sh        # sets core.hooksPath -> .githooks
```

## pre-push — SMS agent eval gate

On every `git push`:

1. Runs the **grader self-test** (free, stdlib only). Failure blocks the push.
2. If the push touches agent behavior (`backend/agent/`, `backend/primitives/`,
   `backend/api/sms.py`, `backend/services/`, or `backend/tests/sms_eval/`),
   runs the **full assertion suite** (`run_assertions.py`).

| Suite result | Meaning | Push |
|--------------|---------|------|
| exit 0 | guards green (targets may still be open) | allowed |
| exit 1 | a **GUARD** regressed | **blocked** |
| exit 2 | gate couldn't run (missing deps/creds) | allowed, with a warning |

The full suite runs the live agent (OpenAI + S3), so it needs the backend venv
and a real `.env`. That's why it's a pre-push gate, not pre-commit — see
`backend/tests/sms_eval/ASSERTIONS.md`.

### Escape hatches
- `git push --no-verify` — skip all hooks once.
- `SKIP_EVAL_GATE=1 git push` — skip just the eval gate.
- `EVAL_PYTHON=/path/to/python git push` — choose the interpreter.
