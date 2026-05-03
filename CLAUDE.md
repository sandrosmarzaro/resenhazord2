# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code
in this repository.

## Project Overview

Resenhazord2 is a **platform-agnostic chatbot**. Python owns the business logic;
platform adapters translate native messages into a unified command surface.

- **Python core** (FastAPI + uvicorn) — all 46 commands, services, business logic,
  Discord adapter. Located at repo root under `bot/`.
- **`gateway/`** (Bun + Baileys, TypeScript) — WhatsApp adapter. Receives messages,
  proactively downloads media, forwards command data + binary frames to Python
  over WebSocket.
- **`bot/adapters/discord/`** (discord.py) — Discord adapter. Slash commands route
  through the same `CommandRegistry` as WhatsApp.
- **Telegram** — planned adapter; not yet implemented.

WhatsApp (and Telegram when it arrives) use a comma-prefix (e.g., `,menu`). Discord
uses native slash commands. Both map to the same command handlers through
`CommandRegistry`. See [docs/architecture.md](docs/architecture.md) for the full
flow, project tree, and adapter structure.

## Rules index

File-scoped standards that Claude applies based on the file being edited:

- [.claude/rules/python.md](.claude/rules/python.md) — scope: `*.py`
- [.claude/rules/typescript.md](.claude/rules/typescript.md) — scope: `*.ts`
- [.claude/rules/git.md](.claude/rules/git.md) — scope: `git *` commands, `.github/**`
- [.claude/rules/testing.md](.claude/rules/testing.md) — scope: `test_*.py`, `*.spec.ts`

Cross-cutting conventions (design, logging, API integration, security, response
formatting) live below in this file because they do not filter cleanly by
extension.

## Code Philosophy

### Object Calisthenics

- Reduce nested blocks; early-return instead of `else`.
- Wrap primitives only for complex domain concepts (JID, CommandName, MediaBuffer).
  Don't wrap a plain `int` just to wrap it.
- First-class collections (`Attachments`, not `list[Attachment]`) when the
  collection has behavior.
- Law of Demeter — at most one dot per chain. `foo.bar.baz()` is a smell.
- No abbreviations (`resp` → `response`, `msg` → `message`).
- Small entities: **≤ 3 public methods / class** (behavior surface), **≤ 7
  attributes / class** (data shape), **≤ 150 LOC / class**, **≤ 4 parameters
  per function**.
- No getters/setters. Tell, don't ask.

### Clean Code — SOLID, DRY, KISS, YAGNI

- **Senior-review standard**: "what would a perfectionist reject?" If the
  architecture is flawed, state is duplicated, or patterns are inconsistent:
  propose and implement the structural fix.
- **No magic numbers** — named constants, `ClassVar`, or `bot/data/` tables.
- **Trust internal code.** Validate only at system boundaries (user input,
  external APIs). Don't add fallbacks, retries, or `try/except` for scenarios
  that can't happen.
- **Tolerate duplication until the third occurrence.** Extract only when the
  shape is stable. Premature abstractions are more expensive than DRY violations.

### TDD

- Write tests **BEFORE or alongside** implementation — never after.
- Run the test suite after every meaningful change, not just at the end.
- Test the **public API only**; private helpers are tested through the public
  surface that uses them.
- **One logical assertion focus per test.** Multiple asserts are fine when they
  verify one behavior.
- Full test patterns and anti-patterns in [.claude/rules/testing.md](.claude/rules/testing.md).

## Common Commands

Prefer Claude slash commands and task runners over memorizing script names.

| Area | Entry point |
|---|---|
| Full test suite (Python + Gateway) | `/test` |
| Local CI (act) | `/ci` |
| Python quality gate | `/check-py` — ruff + format:check + basedpyright |
| Gateway quality gate | `/check-ts` — eslint + tsc + prettier |
| Browse rules/ | `/rules` |
| Python tasks | `uv run task --list` |
| Gateway scripts | `cd gateway && bun run` |
| Docker | `docker compose build && docker compose up -d` |

Individual task definitions live in `pyproject.toml` under `[tool.taskipy.tasks]`
and `gateway/package.json` under `"scripts"`.

**Git hooks** (pre-commit, pre-push): ruff lint + format, gitleaks secret scan,
large-file check, merge-conflict check, eslint, `tsc --noEmit`, prettier check.

## Architecture

Full message flow, ports & adapters, project tree, command system, cache layers,
singletons: [docs/architecture.md](docs/architecture.md).

## Git

Branching strategy and release flow: [docs/git-flow.md](docs/git-flow.md).
Commit mechanics (atomicity, staging, message format):
[.claude/rules/git.md](.claude/rules/git.md).

## Logging

Gateway uses `@sentry/bun` + structured logs. Python uses `sentry-sdk` +
`structlog`. Full guide (init, capture patterns, breadcrumbs, scoped context,
CLI querying, test mocks): [docs/logging.md](docs/logging.md).

## Testing framework summary

- **Gateway**: Vitest with globals enabled. Fixtures in
  `gateway/tests/fixtures/index.js` (`GroupCommandData`, `PrivateCommandData`).
  `createMockWhatsAppPort()` for WhatsApp-aware commands.
- **Python**: pytest + anyio (`@pytest.mark.anyio`). Factories in
  `tests/factories/`. Shared fixtures in `tests/conftest.py`: `mock_whatsapp`,
  `mock_mongodb_collection`, `mock_subprocess`.
- Full anti-patterns and authoritative rules:
  [.claude/rules/testing.md](.claude/rules/testing.md).

## Response Formatting

Bot output conventions (titles, stats layout, quote blocks, spacing, errors):
[docs/response-conventions.md](docs/response-conventions.md).

## External API Integration

Test real endpoints first; pre-download buffers; disable retries for slow APIs;
verify fallbacks independently; test asset URLs with the exact headers the CDN
expects. Full guide: [docs/api-integration.md](docs/api-integration.md).

## Security

CommandParser regex safety + `argsPattern` ReDoS prevention:
[docs/security.md](docs/security.md).

## Tooling preference — CLI over MCP

Prefer CLI tools over MCP servers when both exist. `gh`, `sentry-cli`, `uv`,
`bun`, `docker`, and `curl` cover this project's needs with zero MCP startup
cost. Install an MCP only when no CLI equivalent exists.

For library docs: prefer reading the dependency's source in the repo + WebFetch
the project's official docs URL over a docs-MCP.

This project disables user-scoped `context7` and `github` MCPs via
`.claude/settings.json` (`disabledMcpjsonServers`). They remain active in other
projects.

## Environment

`.env` at the repo root (see `.env.example`) holds WhatsApp JIDs, Gemini API
keys, MongoDB URI, TMDB tokens, Sentry DSNs, and Discord bot token. Symlinked
into `gateway/.env` for local development.
