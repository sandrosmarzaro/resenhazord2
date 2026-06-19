# Security

## CommandParser — regex safety

`CommandParser.replaceDiacritics()` (`gateway/src/parsers/CommandParser.ts`) escapes ASCII regex metacharacters before replacing non-ASCII chars with `.`:

```ts
s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/[^\x00-\x7F]/g, '.');
```

This means command `name`, `aliases`, `flags`, and `options[].values` are safe to use even if they contain chars like `+`, `|`, `(`, etc. Non-ASCII chars still intentionally become `.` (matches the unaccented equivalent).

## argsPattern — avoid ReDoS

Never use nested quantifiers inside repeating groups (e.g. `(?:@\d+\s*)*`). The outer `\s*` injected by `buildRegex()` creates overlap and causes catastrophic backtracking.

**Safe pattern** — separate the whitespace outside the repeating unit:

```ts
// Bad — nested quantifiers cause ReDoS
argsPattern: /^(?:@\d+\s*)*$/;

// Good — no nested overlap
argsPattern: /^(?:@\d+(?:\s+@\d+)*)?$/;
```

The outer `?` handles the optional/empty case. `\s+` between mentions eliminates ambiguity with the surrounding `\s*` injected by the parser.

## Dependency cooldown — supply-chain

New releases are held out of resolution for 7 days, giving a compromised release a review window.

- **bun**: `gateway/bunfig.toml` → `[install] minimumReleaseAge = 604800` (native, at resolve; `minimumReleaseAgeExcludes` to exempt).
- **uv**: a global `exclude-newer` is unsatisfiable against the fresh LangChain floors, so the cooldown is audited not baked: `scripts/check_dep_cooldown.py` (task `cooldown:check`, `security-py` CI job) flags non-allowlisted packages in `uv.lock` younger than 7 days without re-resolving. LangChain/LangGraph/LangSmith are allowlisted. On upgrades: `uv lock --upgrade --exclude-newer "7 days"`.

## Aikido — access

Findings come through the official plugin (`aikido@claude-plugins-official`, MCP `@aikidosec/mcp`), not the REST API. Token lives in `.env` as `AIKIDO_MCP_TOKEN`; the MCP reads `AIKIDO_API_KEY` (precedence over browser login). Headless launch: `AIKIDO_API_KEY="$(grep '^AIKIDO_MCP_TOKEN=' .env | cut -d= -f2-)" claude`. MCP attaches at session start — restart after installing.

- **Feed is paid**: free-tier MCP/REST return `400 - only available for paying customers`; read it via the logged-in browser dashboard (`/api/issues/listGroupedIssues`).
- **Local scan is free**: `aikido_full_scan` (SAST + secrets only — no SCA/feed).
- The token is MCP-only and rejected by the REST API; keep it in `.env`, never print it.
