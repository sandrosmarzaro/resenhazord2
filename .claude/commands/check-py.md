Python quality gate: lint, format check, and type check.

Run these sequentially and stop at the first failure:

1. `uv run task lint` — ruff check
2. `uv run task format:check` — ruff format --check
3. `uv run task typecheck` — basedpyright

If any step fails, show the relevant errors and stop. Do not auto-fix; the user
decides whether to apply fixes or investigate the root cause first.
