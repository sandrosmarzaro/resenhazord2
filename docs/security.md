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

## Sonar S2245 — `random` is not a vulnerability here

SonarCloud flags every changed line that calls `random.choice`, `random.randint` or
`random.shuffle` with `python:S2245` ("pseudorandom generator"). The CI step "Fail on new
Sonar issues" then fails the PR. In this repo `random` only picks content to show (a page,
a player, a club, a lineup order), so these are false positives. Keep `random` with
`# noqa: S311` (the ruff equivalent) and do not switch to `secrets` just to quiet Sonar.

Resolve them as **false positive** in SonarCloud with a one-line reason, then rerun the
failed job (`gh run rerun <run> --failed`). Through the API, with `SONAR_TOKEN` read from
`.env` and never printed:

- list: `GET /api/issues/search?componentKeys=resenhazord2&pullRequest=N&resolved=false`
  (basic auth `token:`; without auth the query returns nothing)
- comment, then resolve: `POST /api/issues/add_comment` and
  `POST /api/issues/do_transition` with `transition=falsepositive`

Only S2245 on content picks qualifies. Any `random` use for tokens, ids or secrets is a real
finding: use `secrets`.

