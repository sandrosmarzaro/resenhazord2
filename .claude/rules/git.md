# Git rules

**Scope**: Bash `git *` commands, `.gitignore`, `.github/**` edits.

Branching strategy and release flow are in [docs/git-flow.md](../../docs/git-flow.md).
This file covers commit-time mechanics.

## Staging

- **Explicit staging**: `git add <file>` — never `git add -A`, `git add .`, or
  `git add -p` without reviewing each hunk. Accidental `.env` or large-binary
  staging is hard to undo from remote.
- Review `git diff --staged` before every commit.

## Message format

- **Conventional commits** with scope: `feat(commands): ...`, `fix(gateway): ...`,
  `docs(claude): ...`, `chore(ci): ...`. Scope is required.
- **Subject**: imperative mood, lowercase after the prefix, ≤ 72 chars, no period.
- **Body** (when warranted): describe the *why*, not the *what* — the diff already
  shows the what. Wrap at 72 chars.
- **No emojis** in messages or bodies.
- **Co-Authored-By** trailer when Claude drafted the commit.

## Atomicity

- **One logical change per commit.** A refactor + a feature + a doc tweak is three
  commits, not one.
- **Commit atomically during implementation, never batched at the end.** When
  phase 1 of a multi-phase task finishes, commit it before starting phase 2.
  Re-stating intent in the commit message is cheaper than untangling a megacommit.

## Rewrites

- **No `--amend` after the commit is pushed.** Amend is for local fixups only.
- **No force push to `main` or `develop`.** Feature branches only.
- **No `--no-verify`** to skip hooks. If a hook fails, fix the cause.

## File-scope guard

- Never delete a file without `grep -r "<basename>"` first. Re-exports, dynamic
  imports, and test fixtures often break silently.

## Queue-contract changes are expand/contract

**Scope**: `.github/**`, broker queue/routing/payload changes.

The two nodes (edge gateway, core bot) deploy independently and in parallel
([ADR 0006](../../docs/adr/0006-two-node-cicd-deploy.md)), so there is always a
window where one node runs the new code and the other the old. Any change to a
**queue contract** — routing key, queue name, binding, or payload schema — must
ship **expand/contract**, never as a breaking rename in one release:

1. **Expand**: add the new queue/field/binding alongside the old; both producer
   and consumer understand both. Deploy.
2. **Migrate**: move producers to the new shape; consumers still accept both.
3. **Contract**: remove the old shape in a later release.

Then deploy order never matters and both deploy jobs run in parallel. A
code-only change with no contract change is covered by reconnect +
at-least-once + graceful drain — no special handling.
