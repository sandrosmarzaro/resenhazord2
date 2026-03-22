# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Resenhazord2 is a WhatsApp chatbot with Python as the primary language:

- **Root** — Python (FastAPI + uvicorn) — all 46 commands, business logic, services
- **`gateway/`** — TypeScript (Bun + Baileys) — WhatsApp adapter, media handling, WebSocket bridge

Commands are prefixed with `,` (comma). The gateway receives WhatsApp messages, proactively downloads any attached media, and forwards everything to the Python engine via WebSocket. All command logic lives in Python.

## MCP Tools

Use the **context7** MCP (`mcp__context7__resolve-library-id` + `mcp__context7__query-docs`) to fetch up-to-date documentation for any library (e.g., `@whiskeysockets/baileys`, `vitest`, `@upstash/redis`).

## Common Commands

### Gateway (TypeScript)

```bash
cd gateway
bun start              # Run the bot
bun test               # Run tests (vitest in watch mode)
bun test:run           # Run tests once
bun test:unit          # Run only unit tests
bun vitest run tests/unit/commands/FooCommand.test.ts  # Run a single test file
bun lint               # ESLint check
bun lint:fix           # ESLint auto-fix
bun typecheck          # TypeScript type checking (tsc --noEmit)
bun format             # Prettier format
bun format:check       # Prettier check
```

### Python (from root)

```bash
uv run pytest -v       # Run tests
uv run ruff check .    # Lint
uv run ruff format .   # Format
uv run basedpyright    # Type check
```

### Docker (from root)

```bash
docker compose build   # Build both services
docker compose up -d   # Start both services
```

**Git hooks:**
- **Pre-commit** (Python): ruff lint+fix, ruff format, gitleaks secret scanning, large file check, merge conflict check
- **Pre-push** (gateway/): eslint, tsc --noEmit, prettier check

## Architecture

The gateway receives WhatsApp messages via Baileys, downloads media proactively, and sends command data + binary frames over WebSocket to Python. Python matches commands via `CommandRegistry`, executes them, and returns `BotMessage[]` responses. Commands raise `BotError` subclasses for user-facing errors, caught centrally by the WebSocket handler.

See [docs/architecture.md](docs/architecture.md) for full details (message flow, command system, ports & adapters, reply builder, CommandConfig, key types, error handling, caches, singletons).

## Code Conventions

- **Runtime**: Python 3.13+ for the bot, Bun (not Node.js) for gateway
- **Modules**: ES modules with `.js` extensions in imports (even for `.ts` files)
- **File naming**: PascalCase for TS classes (e.g., `OiCommand.ts`), snake_case for Python (e.g., `command_parser.py`)
- **Exports**: Default exports for TS class files, named exports for data files
- **Data files**: Large lookup tables, emoji maps, and static datasets belong in `bot/data/`. Do not define big mappings inline in service or command files.
- **No module-level variables**: Avoid `const FOO = ...` at module scope in service/command files. Use `private static readonly` class attributes for constants that belong to a class.
- **Formatting**: Prettier for TS (single quotes, semicolons, 2-space indent, 100 char width), Ruff for Python (single quotes, 100 char width)

### Python Code Quality

Follow PEP 8 and these principles: **DRY**, **SOLID**, **KISS**, **YAGNI**.

- **No magic numbers** — use named constants to describe every numeric literal. Place
  constants as class attributes (`MAX_PAGE = 50`) or in `bot/data/` files, never
  as bare numbers in logic. Use `from http import HTTPStatus` for HTTP status
  comparisons — never compare against bare integer literals
- **Early returns** — prefer returning early to reduce nesting. Avoid deeply nested
  if-elif-else blocks; flatten with guard clauses
- **Dict mapping over if-elif chains** — when dispatching on a value (e.g., file
  extension, content type), use a dict lookup instead of multi-branch conditionals.
  Exception: 2-branch if-else is fine
- **No suppressing lint/format warnings** — do not add `# noqa`, `# type: ignore`, or
  `# fmt: off` without strong justification. Only suppress for genuinely unavoidable
  cases (e.g., `# noqa: S311` for non-crypto `random` usage). Ask the user before
  adding a new suppression
- **No module-level variables** — never define bare `FOO = ...` at module scope in
  command or service files. Use class attributes (with `ClassVar` for mutable types)
  for constants that belong to a class, or place shared data in `bot/data/`
  modules. The only exception is `logger = structlog.get_logger()`
- **Data files** — all dicts, lists, sets, and lookup tables (even small ones) belong in
  `bot/data/` as named exports. Import them in the command file. Never define
  inline data structures in command or service files
- **Polymorphic behavior** — prefer `to_dict()` / `__str__()` methods on data classes
  over isinstance chains. Keep serialization logic close to the data it describes

## Commit Conventions

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

## Testing

### Gateway (TypeScript)

- **Framework**: Vitest with globals enabled
- **Fixtures**: `gateway/tests/fixtures/index.js` provides `GroupCommandData` and `PrivateCommandData` factories (using Fishery)
- **Setup**: `gateway/tests/setup.ts` mocks external dependencies (pino, mongodb, @sentry/bun)
- **WhatsApp mock**: `createMockWhatsAppPort()` from `gateway/tests/fixtures/factories/MockWhatsAppPort.ts`

### Python

- **Framework**: pytest with anyio for async tests (`@pytest.mark.anyio`)
- **Mocking**: Use `pytest-mock`'s `mocker` fixture exclusively — never `from unittest.mock import ...`
- **HTTP mocking**: Use `respx` with `respx_mock` fixture for HTTP calls (MockRouter pattern)
- **Factories**: `GroupCommandDataFactory` and `PrivateCommandDataFactory` from `tests/factories/command_data.py`
- **Shared fixtures** in `tests/conftest.py`:
  - `mock_whatsapp` — AsyncMock with WhatsApp port defaults
  - `mock_mongodb_collection(name)` — factory that returns a mocked collection
  - `mock_subprocess(target, calls=[...])` — factory for mocking `asyncio.create_subprocess_exec`
- **Pattern**: AAA (Arrange-Act-Assert) with blank lines between sections
- **Organization**: Group tests by behavior in classes (e.g., `TestCreate`, `TestDelete`, `TestErrors`)
- **No docstrings** in test files — test names and code should be self-documenting
- **Config**: `pyproject.toml` under `[tool.pytest.ini_options]` and `pytest.toml`

## Sentry

Gateway uses `@sentry/bun` for error tracking and structured logging. See [docs/sentry.md](docs/sentry.md) for setup, structured logs, error capture, breadcrumbs, CLI queries, and test mocks.

## AI Guidelines

- Always run `cd gateway && bun format` after editing TS code and verify no lines exceed 100
  characters
- Always run `cd gateway && bun typecheck` after TS changes and distinguish between pre-existing
  vs newly introduced errors
- Always run `cd gateway && bun test:run` after TS changes and verify all previously passing
  tests still pass
- Always run `uv run ruff check . && uv run ruff format --check .` after Python changes
- Always ask/talk about of implementation of code, which design use
  pattern/library/algorithms/architecture/design system, suggesting and
  listing alternatives approaches (prefer free/freemium ways) with pros and cons
  for each. To rest any debut of how make the instructions
- When adding fields to object literals in config blocks, prefer multi-line
  formatting if the single-line form would exceed 100 chars
- Always commit changes using [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
  and atomic commits — each commit should represent one logical change. Commit as you go.

## Response Formatting

Conventions for bot response text and image captions (title formatting, stats layout, quote blocks, spacing, errors). See [docs/response-conventions.md](docs/response-conventions.md) for full details.

## External API Integration

Guidelines for integrating external APIs (test first, pre-download buffers, disable retries for slow APIs, test asset URLs with headers, verify fallbacks independently). See [docs/api-integration.md](docs/api-integration.md) for full details.

## Security

CommandParser regex safety and argsPattern ReDoS prevention. See [docs/security.md](docs/security.md) for details.

## Environment

Requires a `.env` file at the repo root (see `.env.example`) with keys for: WhatsApp JIDs, Gemini API, MongoDB URI, TMDB, and other service credentials. Symlinked into `gateway/.env` for local development.
