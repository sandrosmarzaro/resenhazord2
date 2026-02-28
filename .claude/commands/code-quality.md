Run all code quality checks: lint, type checking, format verification, and tests.

Run these four commands in parallel and report the results:

1. `bun run lint` - ESLint check
2. `bun run typecheck` - TypeScript type checking (`tsc --noEmit`)
3. `bun run format:check` - Prettier format check
4. `bun run test:run` - Vitest tests (single-run mode)

After all checks complete, provide a summary indicating which checks passed and which failed. If any check fails, show the relevant errors.
