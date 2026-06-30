---
status: accepted
date: 2026-06-24
---

# 0012 — Relational store for per-group config; no REST surface

The project wants the REST-stack keywords — SQLAlchemy, Alembic, a relational
database, JWT — for résumé completeness, the same keyword-breadth motive behind
[ADR 0007](./0007-agent-frameworks-behind-ports.md). The honest problem was the
reverse of the usual one: a stack in search of a use-case. Per-group command
configuration ([PRD](../prd-per-group-config.md)) is that use-case — runtime,
admin-controlled enable/disable of commands per chat across the three platforms,
with NSFW off by default. It is genuinely relational (constraint-heavy, low-churn,
schema-stable) where the existing Mongo data is document-shaped (high-churn content,
lists, counters). The tension: how much of the REST stack does this feature actually
justify, versus what gets bolted on as keyword theater carrying real cost — a second
database on a 1 GB node, and, for REST, a public attack surface on a free-tier VPS.

## Decision

**Adopt Neon serverless Postgres + SQLAlchemy 2.0 (async, `asyncpg`) + Alembic as a
second, polyglot store holding per-group config only. Mutate it through an in-chat
`,config` command. Build no REST API and no JWT.**

- **Polyglot seam.** Relational owns config/settings; Mongo keeps content, lists,
  and counters. The split is along data shape, not convenience: rows keyed on
  `(platform, native_id)` with uniqueness constraints and enum-checked values on one
  side, documents on the other.
- **Config is stored as override deltas, not a matrix.** `chat` carries a
  `default_policy` (`OPEN` | `CURATED`); `command_override` rows record only an
  admin's deviation from the code-defined default. Absent a row, the default derives
  from the existing `CommandScope`. NSFW-off therefore costs zero new data — it is
  already the scope default; a group opts in with one override row.
- **The write path is `,config` in chat**, authorized by the platform's own admin
  check through a new unified `is_admin(chat, sender)` port (WhatsApp reuses the
  existing `group_metadata` RPC; Discord and Telegram follow). Not HTTP.
- **No REST, no JWT.** The bot reads config in-process via SQLAlchemy; nothing else
  calls it. A REST admin API would guard, with a token, a parallel HTTP path that
  duplicates `,config` and that no client — no dashboard, no app — actually calls.

The senior signal is not "shipped a relational DB and an auth layer." It is
**adding the relational store where the data is relational, and refusing the REST/JWT
layer because it has no consumer** — the explicit no is the decision worth recording.
SQLAlchemy, Alembic, async Postgres, and polyglot persistence are the defensible
keywords here; REST/JWT over a single in-process reader would have been the
indefensible ones.

## Considered options

- **Reuse Mongo — one `group_config` collection.** Zero new infrastructure, smallest
  diff. Rejected: it leaves SQLAlchemy/Alembic/relational with no production home, so
  the whole stack reduces to a contrived demo over data that does not need it —
  exactly the "no real use-case" doubt that started this. If the relational keywords
  are worth anything, they are worth a job that is actually relational.
- **Public REST + JWT + hardening** (HTTPS reverse proxy, rate-limit, Fail2Ban,
  firewall). Adds a real ops-hardening artifact. Rejected: it is precisely the
  DoS / injection / XSS surface that is not worth opening on a free-tier VPS, for an
  endpoint with no caller, duplicating a write path the chat platforms already
  authorize.
- **Internal-only REST + JWT** (bind `127.0.0.1`, reach via SSH tunnel / Tailscale).
  No public surface, keeps the REST/JWT/Swagger artifact. Rejected: still a lock on a
  door nobody opens. With one in-process reader and platform-level admin authz already
  doing the real work, JWT is decorative and the endpoints mirror `,config` for no
  consumer. Revisit only if a web admin dashboard becomes a real goal — at which point
  the dashboard is the JWT client and this ADR is superseded.
- **Turso / libSQL** instead of Postgres. Simplest ops, edge reads. Rejected: SQLite
  semantics, not Postgres — a weaker relational story for the keyword purpose and a
  different SQLAlchemy dialect than the target.

## Consequences

- **A second datastore lands on the core node.** New connection (`asyncpg`), new
  Alembic migration lifecycle, a new `DATABASE_URL` secret. Contained to the core
  node — the edge gateway never touches Postgres. Neon's auto scale-to-zero +
  auto-resume keeps the 100 CU-hour free budget intact precisely because reads are
  cached.
- **Config sits on the hot path** (`CommandHandler._dispatch`, every message), so an
  in-process TTL cache with write-invalidation is mandatory, not optional — a DB
  round-trip per command would burn CU-hours and add scale-to-zero cold starts to
  user latency. Single-consumer coherence today; the seam to Upstash pub/sub
  invalidation is noted for any future second worker (PRD §caching).
- **No queue-contract change.** The feature is purely additive on one node, so the
  expand/contract discipline ([ADR 0006](./0006-two-node-cicd-deploy.md), git rules)
  does not apply.
- **A new cross-platform `is_admin` abstraction** is required; it did not exist (only
  WhatsApp resolved admins, ad hoc, via `group_metadata`). WhatsApp ships first,
  Discord and Telegram follow — the `platform` column carries data the later adapters
  will use.
- **Infra scopes stay code-locked.** `DISABLED` / `DEV` / `ADMIN` / `INTERNAL` are
  checked before the per-group layer and are never reachable by a group admin's
  override; only `PUBLIC` and `NSFW` are togglable. The config layer cannot become a
  privilege-escalation path.
