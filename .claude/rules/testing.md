# Testing rules

**Scope**: `test_*.py`, `tests/**/*.py`, `*.spec.ts`, `*.test.ts`, `gateway/tests/**`.

Things a test runner cannot catch — anti-patterns that make tests green without
proving the code works. Frameworks in use: pytest + anyio (Python), Vitest (Gateway).

## TDD loop

- Write tests **BEFORE or alongside** the implementation — never after.
- Run the suite after every meaningful change, not just at the end.
- Red → Green → refactor. A failing test proves the test works; jumping to green
  on the first try is a warning sign, not a win.

## What to test

- **Public API only.** Private functions are covered through the public surface
  that uses them. Testing private helpers couples tests to implementation and
  blocks refactors.
- **One logical assertion focus per test.** Multiple `assert` statements are fine
  when they verify a single behavior (e.g., asserting both `status_code` and
  response body of one request).
- **Group by behavior**, not by method name. Python: `class TestCreate`,
  `class TestDelete`, `class TestErrors`. Vitest: nested `describe` blocks.
- **No docstrings in test files.** Test names and AAA structure self-document.
- **AAA pattern** — Arrange / Act / Assert with blank lines between sections.

## Anti-patterns (mocking)

- **No mock-compared-to-mock.** `assert m.return_value == m.return_value` is
  always true and proves nothing. Compare against real values.
- **No smoke tests that only import.** A test that imports a module and asserts
  nothing useful is dead weight. Exercise behavior.
- **Assert on arguments, not just calls.** `mock.assert_called_once_with(...)`,
  not `mock.assert_called_once()` / `mock.called`. If you don't care about args,
  the mock is over-scoped.
- **Don't mock what you don't own.** Mock your adapter (`WhatsAppPort`,
  `AxiosClient`) — not the underlying SDK (Baileys, httpx internals). Mocking
  third-party internals breaks on every dependency upgrade.
- **Use `respx` for HTTP**, not hand-rolled mock responses. Real URLs + real
  status codes catch bugs hand-mocks miss.
- **`pytest-mock`'s `mocker` fixture only** — never `from unittest.mock import ...`
  at the top of a test file.

## Anti-patterns (async)

- **No `asyncio.sleep` for synchronization.** Use `asyncio.Event`, `asyncio.wait`,
  or equivalents. Sleeps make tests flaky and slow.
- In Vitest, prefer `vi.waitFor(() => ...)` over `await new Promise(r => setTimeout(r, N))`.

## Python fixtures

- **Factories**: `GroupCommandDataFactory` / `PrivateCommandDataFactory` from
  `tests/factories/command_data.py`. Don't hand-construct `CommandData`.
- **Shared mocks** in `tests/conftest.py`: `mock_whatsapp`, `mock_mongodb_collection`,
  `mock_subprocess`. Reuse them — don't re-invent per test file.
- **`@pytest.mark.anyio`** on async tests.

## Gateway fixtures

- `gateway/tests/fixtures/index.js` exports `GroupCommandData` and
  `PrivateCommandData` factories (Fishery).
- `createMockWhatsAppPort()` from
  `gateway/tests/fixtures/factories/MockWhatsAppPort.ts` for commands that hit
  WhatsApp.
- `gateway/tests/setup.ts` mocks pino, mongodb, `@sentry/bun` — extend there when
  a new external dep shows up.

## E2E

- Integration tests hit a real local DB where practical. Mock-only integration
  tests create false confidence. Document when a shortcut is taken and why.
