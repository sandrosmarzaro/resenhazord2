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

A freshly published release can be a compromised or hijacked version. Both
ecosystems hold new releases out of resolution for a 7-day review window.

**Gateway (bun)** — native, enforced at resolve time:

```toml
# gateway/bunfig.toml
[install]
minimumReleaseAge = 604800  # 7 days, in seconds
```

Add `minimumReleaseAgeExcludes = ["pkg"]` for any dependency that must track
fresher than the window.

**Core (uv)** — uv has no baked-in equivalent that survives this project's
intentionally fresh LangChain/LangGraph floors: the stack republishes weekly,
so a global `exclude-newer` makes `uv sync` unsatisfiable. Instead the cooldown
is audited, not baked. `scripts/check_dep_cooldown.py` (task `cooldown:check`,
run in the `security-py` CI job) checks the committed `uv.lock` for
non-allowlisted packages younger than 7 days **without re-resolving** — so it
never trips the LangChain cascade. The LangChain/LangGraph/LangSmith prefixes
are allowlisted as accepted risk; keep that list tight.

When intentionally upgrading, apply the window at resolve time:

```bash
uv lock --upgrade --exclude-newer "7 days"
# add --exclude-newer-package <pkg>=P0D for each tracked-fresh dep uv complains about
```

## Aikido — vulnerability scanning access

Aikido findings are reached through the official Claude Code plugin
(`aikido@claude-plugins-official`, MCP server `@aikidosec/mcp`), **not** the REST
API. The personal token lives in `.env` as `AIKIDO_MCP_TOKEN`; the MCP package
reads it from the `AIKIDO_API_KEY` env var, which takes precedence over the
browser sign-in. Launch from the repo root so the server authenticates headlessly:

```bash
AIKIDO_API_KEY="$(grep '^AIKIDO_MCP_TOKEN=' .env | cut -d= -f2-)" claude
```

MCP servers attach only at session start — installing the plugin mid-session
does not make its tools live; restart first.

**Caveats / dead ends:**

- The **issue feed is a paid feature**. On the free tier the MCP
  `aikido_issues_list` returns `400 - This action is only available for paying
  customers`. The gate is on the capability, not the transport — the public REST
  API hits the same wall (and needs separate OAuth client credentials anyway).
- The dashboard **web feed is readable via the logged-in browser session** (GitHub
  OAuth) even on the free tier: `app.aikido.dev/api/issues/listGroupedIssues`.
- **Local scanning is free**: `aikido_full_scan` (SAST + secrets) runs locally on
  files you pass in. It does not read the historical feed and does not cover
  dependency CVEs (SCA), IaC, container, cloud, or license/EOL findings.
- The `AIKIDO_MCP_TOKEN` is MCP-only and is rejected by the REST API; never print
  it — keep it in `.env`.
