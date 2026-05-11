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
4. Push and open PR **targeting `develop`**
5. Require CI green + 1 approval, then **squash merge**
6. Delete branch after merge

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
7. **No back-merge needed** — `develop` already contains the version bump and CHANGELOG update.

## Hotfix workflow

For urgent production fixes that can't wait for the next release:

1. `git checkout main && git pull && git checkout -b hotfix/description`
2. Fix, commit with Conventional Commits, push
3. Open PR targeting `main`
4. Merge with **"Create a merge commit"** (same reason as release)
5. Pipeline deploys and tags. After the pipeline finishes, bump version on develop with `uv run task release` and push so `develop` stays in sync.

## Merge-strategy summary

| Merge target                   | Strategy                 | Reason                                                              |
| ------------------------------ | ------------------------ | ------------------------------------------------------------------- |
| `develop` ← feature/fix/chore  | **Squash**               | Clean history; squash subject itself is a Conventional Commit       |
| `main` ← `develop`             | **Merge commit (`--no-ff`)** | Preserves every Conventional Commit for commitizen               |
| `main` ← `hotfix/*`            | **Merge commit**         | Same reason                                                         |