Gateway (TypeScript) quality gate: lint, type check, and format check.

Run these sequentially and stop at the first failure:

1. `cd gateway && bun lint` — ESLint
2. `cd gateway && bun typecheck` — `tsc --noEmit`
3. `cd gateway && bun format:check` — Prettier

If any step fails, show the relevant errors and stop. Do not auto-fix; the user
decides whether to apply fixes or investigate the root cause first.
