# Git Flow

## Conventional Commits

This project uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

| Type         | When to use                                                      |
| ------------ | ---------------------------------------------------------------- |
| `feat:`      | New feature or capability                                        |
| `fix:`       | Bug fix                                                          |
| `refactor:`  | Code restructuring without changing behavior                     |
| `test:`      | Adding or updating tests                                         |
| `docs:`      | Documentation changes                                            |
| `style:`     | Formatting, whitespace, semicolons (no logic change)             |
| `ci:`        | CI/CD pipeline changes (GitHub Actions, Docker, deploy scripts)  |
| `chore:`     | Tooling, configs, dependencies, maintenance                      |
| `perf:`      | Performance improvements                                         |
| `build:`     | Build system or external dependency changes                      |

### Rules

- **Subject line**: imperative mood, lowercase, no period, max ~72 chars
- **Body** (optional): explain *why*, not *what* — the diff shows what changed
- **Scope** (optional): area affected, e.g. `feat(command):`, `fix(cache):`
- **Breaking changes**: add `!` after type or `BREAKING CHANGE:` in footer
- **Atomic commits**: each commit should represent one logical change
- **Commit as you go** — create each commit immediately after completing its logical unit of work, not after finishing all changes

### Examples

```
feat: add hentai command with hitomi default and nhentai fallback
fix(cache): handle Redis connection timeout gracefully
refactor: move TypeScript service to gateway/
test: add Python unit and integration test structure
```

## Branches

This project uses a **two-permanent-branch** flow. Direct pushes to either are blocked — all changes go through PRs.

| Branch    | Purpose                                                            | Default | Auto-release |
| --------- | ------------------------------------------------------------------ | ------- | ------------ |
| `main`    | Production. `Pipeline` workflow runs deploy + tag.                 | No      | Yes          |
| `develop` | Integration. Accumulates PRs between releases.                     | Yes     | No           |

### Short-lived branches

| Prefix                                                   | Forks from | PRs into                                | Example                        |
| -------------------------------------------------------- | ---------- | --------------------------------------- | ------------------------------ |
| `feat/*`, `fix/*`, `refactor/*`, `docs/*`, `chore/*`, … | `develop`  | `develop`                               | `feat/add-fipe-command`        |
| `hotfix/*`                                               | `main`     | `main` (then back-merge into `develop`) | `hotfix/fix-cache-timeout`     |

## Daily workflow (features / fixes / chores)

1. Sync: `git checkout develop && git pull`
2. Branch: `git checkout -b feat/description`
3. Commit using Conventional Commits (atomic — one logical change per commit)
4. Push and open PR **targeting `develop`**, assigned to the repo owner
   (`gh pr create --assignee @me`). When the work comes from an issue, end the body
   with `Closes #N` so the merge closes it.
5. Require CI green + 1 approval, then **squash merge**
6. Delete branch after merge

### Stacked PRs

When a change depends on an open PR, branch from that PR's branch and open the new PR **with
it as the base**. `Check` runs on any base and only for the side (Python / gateway) the PR
touches. When the parent merges, GitHub deletes its branch and retargets the child to
`develop`. `develop` doesn't require branches to be up to date, so the child keeps its green
checks and merges without another CI run.

**Merge a parent that still has an open child with "Create a merge commit", not squash.**
Its commits then become ancestors of `develop`, so the child's diff shows only its own
changes and needs no rebase. Every commit on the parent must already be a Conventional
Commit, since they all land on `develop` and commitizen reads each one. The last PR of the
stack (no open child) squash-merges as usual.

Why: a squash puts the parent's changes on `develop` under a new SHA while the child still
carries the original commits. GitHub then lists the parent's commits and files in the
child's diff, and the child turns `CONFLICTING` when it edits or deletes a file the parent
changed (#232 after #230: the parent edited `agent_executor.py`, the child deleted it). The
fix is `git rebase --onto develop <parent-branch>`, which needs a force push, and the
pre-push hook blocks that unless you run it yourself. Without force, `git merge
origin/develop` into the child and resolve the conflicts once; the final squash drops that
merge commit.

To restack after amending a lower branch, run `git rebase --update-refs <base>` from the top
of the stack (this also needs a force push).

Never dodge the force-push block by republishing a rebased branch under a new name
(`feat/x-v2`, `feat/x-v3`). Each copy leaves a stale remote branch behind, splits the
branch's history from its PR, and hides the rewrite the hook exists to surface (#252–#256
did this). Merge parents with a merge commit, or `git merge origin/develop` into the
child, or ask the owner to run `git push --force-with-lease` on the feature branch.

The squash-merge commit subject **must itself be a Conventional Commit** (`feat: …`, `fix(scope): …`, …) — commitizen reads every commit on `develop` and infers the version bump from these subjects.

## Release workflow (`develop` → `main`)

When `develop` has accumulated enough changes to release:

1. **Bump version on develop:** `uv run task release` (runs `cz bump --changelog`)

   This reads conventional commits since the last tag, bumps `pyproject.toml` version, and updates `CHANGELOG.md`. It deletes the local tag so the tag is created on `main` by CI later.
2. Push to develop: `git push origin develop`
3. Open a PR **from `develop` into `main`** using the Release PR template (append `?template=release.md` to the PR URL, or pick it from the template dropdown).
4. Confirm CI is green.
5. **Merge with "Create a merge commit"** — not squash, not rebase. This is **mandatory**.

   Why: the merge commit must include every conventional commit so the version bump and CHANGELOG in the PR already reflect the correct changes. A squash would collapse history.
6. `Pipeline` runs automatically on `main`: lint → test → build → deploy → register deployment → tag.

   The `tag` job reads `project.version` from `pyproject.toml` and creates a `v$VERSION` tag on the merge commit.
7. Pipeline's `back-merge` job then merges `main` into `develop`, so `develop` holds the release merge commit too. Nothing to do by hand; it exits early when `develop` already contains `main`.

## Hotfix workflow

For urgent production fixes that can't wait for the next release:

1. `git checkout main && git pull && git checkout -b hotfix/description`
2. Fix, commit with Conventional Commits (`fix(scope): …` only)
3. **Bump the patch version on the hotfix branch:** `uv run task release`, then push

   Only `fix:` commits sit between the last tag and the branch, so `cz bump` picks PATCH (e.g. `2.10.0` → `2.10.1`) and writes the CHANGELOG entry. If it proposes MINOR, a `feat:` slipped into the hotfix: move it to `develop`.

   Why on the branch: the `tag` job tags whatever `project.version` says. A hotfix merged without a bump still carries the last released version, so the job finds that tag already exists and skips it, and production runs code no tag identifies. That happened with #226.
4. Open PR targeting `main`
5. Merge with **"Create a merge commit"** (same reason as release)
6. Pipeline deploys, tags `vX.Y.Z`, creates the GitHub release and back-merges `main` into `develop`, so `develop` receives the fix, the new version and the CHANGELOG entry. No manual step.

## Merge-strategy summary

| Merge target                   | Strategy                 | Reason                                                              |
| ------------------------------ | ------------------------ | ------------------------------------------------------------------- |
| `develop` ← feature/fix/chore  | **Squash**               | Clean history; squash subject itself is a Conventional Commit       |
| `develop` ← parent of a stack  | **Merge commit**         | Child keeps a clean diff; no rebase or force push (see Stacked PRs)  |
| `main` ← `develop`             | **Merge commit (`--no-ff`)** | Preserves every Conventional Commit for commitizen               |
| `main` ← `hotfix/*`            | **Merge commit**         | Same reason                                                         |