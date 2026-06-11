# Python rules

**Scope**: `*.py`

Things that lint, format, or typecheck cannot catch. Follow PEP 8 plus the below.

## Structure

- **Early returns** — flatten with guard clauses. Avoid nested `if`/`elif`/`else`.
  Two-branch `if`/`else` is fine; three or more branches → dict dispatch.
- **Dict dispatch over `elif` chains** — when selecting behavior on a value (file
  extension, content type, command key), use a dict lookup, not `elif`.
- **Polymorphism over isinstance chains** — `to_dict()`, `__str__()`, `render()`
  methods on data classes. Keep serialization next to the data it describes.
- **No `__init__.py`** — Python 3.3+ uses namespace packages (PEP 420); they are useless.

## Constants and data

- **No magic numbers** — every numeric literal has a named constant. HTTP status
  comparisons use `from http import HTTPStatus`, never `== 200`.
- **`ClassVar[dict[...]]` for class-scoped mutable constants** — avoid bare
  module-level dicts or lists.
- **No bare module-level `FOO = ...`** in command / service / adapter / handler
  files. Only exception: `logger = structlog.get_logger()`.
- **Lookup tables live in `bot/data/`** — dicts, lists, sets, enum maps, emoji
  tables, even small ones. Named exports only. No inline data in command files.

## Broker idempotency

- **At-least-once delivery means commands can be redelivered** after a crash gap
  ([ADR 0001](../../docs/adr/0001-at-least-once-delivery.md)). Most commands are
  replay-safe (pure render, `$addToSet`/`$pull`, idempotent WhatsApp writes).
- **Any new non-idempotent command** (economy, points, counters — anything
  money- or state-meaningful) must either be made replay-safe or gate on the
  `CommandData.message_id` idempotency key (a short-TTL Redis `SET` inbox). Don't
  add a `$inc`-style counter without one. The two known exceptions (`,borges`,
  steal-group counter) are tolerated vanity numbers, not a precedent.

## Logging

- Always `structlog.get_logger()` at module top — never `logging.getLogger`.
- No `print` in runtime code.

## Suppression

- **No `# noqa`, `# type: ignore`, `# fmt: off`** without written justification in
  the line above. Ask before adding a new suppression. Only acceptable without
  approval: `# noqa: S311` for non-crypto `random` usage.

## Naming

- **English for file names, class names, functions, variables.** User-facing
  trigger strings (`CommandConfig.name`, `aliases`), reply text, and
  `menu_description` stay pt-br — that is product voice, not code naming.
- **No abbreviations** — `resp` → `response`, `msg` → `message`, `cfg` →
  `config`. Loop counters (`i`, `j`) are the only single-letter vars.
- Proper-noun acronyms (FIPE, IBGE, CNPJ) keep their casing.

## Size limits

See CLAUDE.md Code Philosophy for the canonical numbers (≤ 3 public methods / ≤ 7
attributes / ≤ 150 LOC per class, ≤ 4 params per function).
