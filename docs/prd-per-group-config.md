# PRD — Per-Group Command Configuration

**Status:** Draft · **Date:** 2026-06-24 · **Owner:** Sandro

Give group admins runtime control over which commands run in their own chat, stored
in a relational database (Neon Postgres) behind SQLAlchemy + Alembic, mutated through
an in-chat `,config` command. NSFW commands are off by default; a chat can opt into a
curated allow-list mode. No REST API, no JWT — see
[ADR 0012](./adr/0012-relational-config-store.md).

## 1. Problem

Command availability is static and global. `CommandScope` (`bot/domain/commands/base.py`)
is declared in code per command; the only runtime gates are `DISABLED` and `DEV` in
`CommandHandler._dispatch`. NSFW gating is hard-coded per adapter (Discord
`handler.py`, Telegram `_nsfw_chat_ids`). A group admin cannot turn a command on or
off for their own group, and there is no per-chat policy. Every group gets the same
surface, and enabling NSFW for one chat means editing code or env.

## 2. Goals

1. **Per-chat command toggles.** A group admin enables/disables an individual
   `PUBLIC` or `NSFW` command for their chat at runtime.
2. **Safe defaults.** NSFW/+18 commands are off until a chat explicitly opts in.
3. **Curated mode.** A chat can flip to deny-by-default, where only explicitly
   enabled commands run (`,only resenhaz`).
4. **Three platforms.** The model keys on `(platform, native_id)` so WhatsApp,
   Discord, and Telegram share one config table.
5. **Real relational stack.** SQLAlchemy 2.0 async + Alembic + Postgres earn a
   genuine production job, not a demo (the keyword motive, honestly placed).

## 3. Non-goals

- **No REST API and no JWT.** The bot reads config in-process; nothing else calls it.
  The in-chat `,config` command is the only write path ([ADR 0012](./adr/0012-relational-config-store.md)).
- **No public VPS port, no new attack surface.** No Fail2Ban/firewall work is in
  scope because nothing new listens publicly.
- **Infra scopes are not configurable.** `DISABLED` / `DEV` / `ADMIN` / `INTERNAL`
  stay code-controlled and are never reachable by a group admin.
- **Not a per-user setting.** Config is per chat, not per participant.
- **Mongo is not migrated.** Existing document data stays in Mongo; only config is
  relational (polyglot, by data shape).

## 4. Domain language

- **Chat** — a single conversation the bot serves, identified by
  `(platform, native_id)`; `type` is `group` or `private`. _Avoid_: room, channel.
- **Default policy** — a chat's baseline: `OPEN` (public commands on, NSFW off) or
  `CURATED` (everything off; overrides are an allow-list). `,only resenhaz` = `CURATED`.
- **Command override** — a stored deviation from the code default for one command in
  one chat: `enabled` true or false. Absence of a row means "use the default."
- **Togglable command** — a command an admin may override: scope `PUBLIC` or `NSFW`
  only. _Avoid_: configurable (too broad).
- **Effective enablement** — the resolved on/off for a `(chat, command)` pair after
  applying policy and overrides over the code default.

## 5. Data model

Two tables, Postgres, managed by Alembic.

```
chat
  id             bigserial PK
  platform       text   not null     -- whatsapp | discord | telegram
  native_id      text   not null     -- WA JID / Discord guild id / TG chat id
  type           text   not null     -- group | private
  default_policy text   not null default 'OPEN'   -- OPEN | CURATED
  unique (platform, native_id)

command_override
  id           bigserial PK
  chat_id      bigint not null references chat(id) on delete cascade
  command_name text   not null
  enabled      boolean not null
  unique (chat_id, command_name)
```

Override deltas, not a 46×N matrix: a row exists only when an admin flips a command,
so adding a command needs no backfill and most chats store nothing.

**Chat-row lifecycle is lazy.** A `chat` row is get-or-created on first need — the
first message seen from it, or the first `,config`/admin action. No enumeration, no
backfill. Because absent rows mean "use code defaults," a chat the bot is already in
behaves correctly *before* any row exists; the row only has to exist at the moment of
its first override or policy write. Existing chats therefore need no onboarding step
for reads (but see §11 for the one-time NSFW seed).

## 6. Resolution logic

`effective_enabled(chat, command)`:

1. If an infra scope applies (`DISABLED` / `DEV` / `ADMIN` / `INTERNAL`), the
   per-group layer is never reached — handled earlier in `_dispatch`.
2. If a `command_override` row exists for `(chat, command)`, return its `enabled`.
3. Else, by policy:
   - `CURATED` → `False` (deny-by-default; overrides are the allow-list).
   - `OPEN` → the code default from `CommandScope` (`PUBLIC` on, `NSFW` off).

NSFW-off and curated mode both fall out of this without special-casing.

## 7. Enforcement point

`CommandHandler._dispatch` (`bot/application/command_handler.py`) gains a step after
the existing scope checks and before `_run_command`:

```
DISABLED -> blocked            (code)
DEV      -> dev only           (code)
ADMIN    -> owner only         (code)
INTERNAL -> official chat only (code)
[NEW] per-group effective check for PUBLIC | NSFW
```

A new `ConfigService` (domain) backed by a `ConfigStorePort` (SQLAlchemy adapter in
`bot/infrastructure/`) answers `effective_enabled`. A disabled command replies with a
short "command off here" notice, mirroring the existing `_DISABLED_MSG` pattern.

## 8. Read caching

Config is read on every message but changes only on a `,config` write.

- **In-process TTL cache** keyed by chat (~60 s), filled on miss from Postgres,
  **invalidated immediately on a `,config` write**. Zero network on the hot path.
- Coherent because the bot is a single consumer on the core node (the broker PRD
  keeps horizontal scale a non-goal but does not preclude it).
- **Seam:** if a second worker is ever added, swap the local invalidation for Upstash
  pub/sub. Not built now.

## 9. Write path — the `,config` command

An `ADMIN`-scoped, admin-gated command in `bot/domain/commands/config.py`. The target
of a verb is a single command name **or** a subtype, resolved uniformly (verb-first):

```
,config                          -> show this chat's policy + active overrides
,config on    <command|subtype>  -> override enabled = true
,config off   <command|subtype>  -> override enabled = false
,config reset <command|subtype>  -> delete the override(s) (back to default)
,config policy open|curated      -> set default_policy
```

`ADMIN` scope (not `PUBLIC`) keeps `,config` off the togglable path, so a `CURATED`
policy can never lock a chat out of its own config. Only `PUBLIC` / `NSFW` command
names are accepted as targets; anything else returns a "not configurable" notice.
Writes invalidate the chat's cache entry.

**Subtype shortcuts** are a macro over the *current* set of togglable commands in a
subtype — they expand to a batch of per-command override writes, then one cache
invalidation. No schema change; no standing category state ([ADR 0012](./adr/0012-relational-config-store.md)
stands). A subtype is the scope `nsfw` or a category `download` / `group` / `random`
/ `info`, and the macro only ever touches that subtype's `PUBLIC` / `NSFW` members.
A command added to a subtype *after* the shortcut is run is not retroactively
included — it keeps its code default until an admin enables it (safe-by-default for
new +18 commands). `,config nsfw on` is the motivating case: opt a chat into all
current +18 commands in one line.

## 10. Admin authorization

`,config` requires the sender to be an admin of the chat. There is no unified admin
check today (only WhatsApp, ad hoc, via `group_metadata`). Introduce a single
`is_admin(chat, sender)` resolved per adapter:

- **WhatsApp** — reuse the existing `group_metadata` RPC (`participant.admin`).
- **Discord** — interaction member permissions (Manage Guild).
- **Telegram** — `getChatMember` status (`administrator` / `creator`).

Private chats have no admin; the sole participant is implicitly authorized for their
own DM.

## 11. Existing-chat migration

**Discovered baseline:** `CommandScope.NSFW` was dead — no command carried it, so the
Discord channel gate *and* the Telegram `telegram_nsfw_chat_ids` gate fired for
nothing, and the +18 commands (`porno`, `hentai`, `rule34`, `fuck`) ran **everywhere
on all three platforms**. Tagging those four with `NSFW` scope (done) activates all
three gates at once. So the cutover changes NSFW behavior on every platform, not just
WhatsApp:

- **WhatsApp** — +18 go **off by default** via the new per-group layer until an admin
  opts in. No seed: there is no prior per-chat state to preserve, and seeding "on
  everywhere" would defeat the safety default.
- **Telegram** — the `telegram_nsfw_chat_ids` gate now actually bites. Preserve those
  chats: seed a `chat` row + `nsfw`-subtype overrides (`enabled = true`) for each.
- **Discord** — the native NSFW-channel gate now actually bites. No seed (channel-level,
  not chat-config).
- **`resenha_jid`** — seed one `chat` row with `default_policy = CURATED` (the "only
  resenhaz" chat).

The migration is a one-time, idempotent seed script (get-or-create, safe to re-run)
reading the existing settings allow-lists — not a full enumeration of every chat.
Every chat not named in those allow-lists adopts the safe default (OPEN, NSFW off)
the moment it is first seen. Announce the cross-platform NSFW change so admins know to
run `,config nsfw on`.

## 12. Rollout phases

1. **Schema + store.** Add `asyncpg` + SQLAlchemy + Alembic; `chat` / `command_override`
   tables; `ConfigStorePort` + adapter; `DATABASE_URL` (Neon) on the core node only.
   Tests against a real local Postgres.
2. **Resolution + enforcement.** `ConfigService` + the `_dispatch` step + in-process
   cache. NSFW now default-off via the new layer; verify parity with current adapter
   gating, then retire the hard-coded paths.
3. **`,config` + WhatsApp admin + NSFW tagging.** The `ADMIN`-scoped command, the
   `is_admin` WhatsApp impl, and tagging the four +18 commands `NSFW` (which also
   activates the previously-dead Discord/Telegram gates). Usable end-to-end on
   WhatsApp groups. *(done)*
4. **Curated policy.** `default_policy` writes + deny-by-default resolution. *(done —
   `,config policy` + resolution)*
5. **Migration seed.** Idempotent script seeding the Telegram allow-list and
   `resenha_jid` (§11); announce the cross-platform change. *(script done —
   `task seed:config`; runs once against Neon at cutover)*
6. **Discord + Telegram `is_admin` + enforcement.** Extend the admin port and wire
   `ConfigService` into the Discord/Telegram handlers, which today call `run` directly
   and so honor only their native NSFW gates, not `,config` overrides/CURATED. The
   table already carries `platform`.

The agent few-shot index (`task index:examples`) is rebuilt whenever commands or
`AGENT_EXAMPLES` change; the `,config` phrasings were added and indexed alongside
phase 3.

## 13. Risks

- **Hot-path latency / CU burn** if caching regresses — mitigated by §8; assert no
  per-command DB hit in tests.
- **NSFW parity regression** — the new default-off must exactly match today's adapter
  gating before the old paths are removed (phase 2 gate).
- **WhatsApp NSFW goes dark at cutover** — +18 commands stop working in every WhatsApp
  group until an admin opts in (§11). Mitigated by announcing it, not by silent seed.
  The migration seed (phase 5) must be idempotent so a re-run never double-writes.
- **Admin RPC cost** — WhatsApp `is_admin` adds a `group_metadata` round-trip to
  `,config`; acceptable because `,config` is rare (write path), not the hot path.
- **Second DB on a 1 GB node** — connection pool sized small; Neon scale-to-zero
  keeps idle cost ~nil. Watched alongside the core node's existing RSS budget.

## 14. Testing strategy

- **Store/adapter** against a real local Postgres (testing rules: real DB over
  mock-only).
- **Resolution** as pure unit tests over the policy × override × scope matrix.
- **Enforcement** through `CommandHandler` with a stubbed `ConfigStorePort`,
  asserting the `_dispatch` order and that infra scopes are never reachable by an
  override.
- **`,config`** through the command's public `run`, asserting admin-gating and cache
  invalidation on write.
