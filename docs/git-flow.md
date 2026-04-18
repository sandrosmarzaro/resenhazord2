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
| `main`    | Production. `Pipeline` workflow runs deploy + semantic-release.    | No      | Yes          |
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

The squash-merge commit subject **must itself be a Conventional Commit** (`feat: …`, `fix(scope): …`, …) — semantic-release reads every commit that lands on `main` later and infers the version bump from these subjects.

## Release workflow (`develop` → `main`)

When `develop` has accumulated enough changes to release:

1. Open a PR **from `develop` into `main`** using the Release PR template (append `?template=release.md` to the PR URL, or pick it from the template dropdown).
2. Confirm CI is green.
3. **Merge with "Create a merge commit"** — not squash, not rebase. This is **mandatory**.

   Why: semantic-release analyzes every commit between the previous release tag and `main` to compute the next version. A squash would collapse many Conventional Commits into one subject and produce the wrong bump (e.g. hiding a `feat` behind a `chore` title). The merge commit preserves every `feat` / `fix` / `BREAKING CHANGE`.
4. `Pipeline` runs automatically on `main`: lint → test → build → deploy → semantic-release → new tag + `CHANGELOG.md`.

## Hotfix workflow

For urgent production fixes that can't wait for the next release:

1. `git checkout main && git pull && git checkout -b hotfix/description`
2. Fix, commit with Conventional Commits, push
3. Open PR targeting `main`
4. Merge with **"Create a merge commit"** (same reason as release)
5. Pipeline deploys and releases a patch version
6. **Back-merge `main` into `develop`** so the fix is present on the integration branch:

   ```
   git checkout develop && git pull
   git checkout -b chore/back-merge-main
   git merge --no-ff main
   ```

   Push and open a PR into `develop` (merge commit, not squash).

## Merge-strategy summary

| Merge target                   | Strategy                 | Reason                                                              |
| ------------------------------ | ------------------------ | ------------------------------------------------------------------- |
| `develop` ← feature/fix/chore  | **Squash**               | Clean history; squash subject itself is a Conventional Commit       |
| `main` ← `develop`             | **Merge commit (`--no-ff`)** | Preserves every Conventional Commit for semantic-release         |
| `main` ← `hotfix/*`            | **Merge commit**         | Same reason                                                         |
| `develop` ← `main` (back-merge)| **Merge commit**         | Preserves hotfix history on `develop`                               |
