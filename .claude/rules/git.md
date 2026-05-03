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
