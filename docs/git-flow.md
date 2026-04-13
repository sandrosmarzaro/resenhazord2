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

## Protected Main

Protected `main` branch — all changes via PR only:

1. Branch from `main`: `git checkout -b feature/description`
2. Make commits with conventional commits
3. Push and open PR against `main`
4. Require 1+ approval, CI passing
5. Squash merge to `main`
6. Delete branch after merge