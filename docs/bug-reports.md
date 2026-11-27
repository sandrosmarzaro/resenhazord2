# Bug reports (`,bug`)

A dev turns a bad bot reply into a GitHub issue that carries everything needed to debug
it. The issue holds the command that produced the reply, its failure and its telemetry,
so nobody has to search Sentry, Loki and Tempo by timestamp.

## Usage

`,bug` is a `CommandScope.DEV` command: only users in the dev list (`,dev`) can run it.

| Platform | How to point at the reply |
|---|---|
| WhatsApp | reply to the bot's message with `,bug [what went wrong]` |
| Telegram | reply to the bot's message with `/bug [what went wrong]` |
| Discord | `/bug args:<message link or id> [what went wrong]`, in the same channel. A slash command can't reply to a message |

The bot answers with the issue link. Without a quoted message it explains the usage.
A reply with no record (older than the retention, or sent before the feature) files
nothing. Without the token it says `,bug` isn't configured.

## How the record is kept

Every command runs inside a `CommandTrail` (`bot/infrastructure/command_trail.py`),
opened by the platform around the command and its reply. While it is open:

- `TrailSpanProcessor` copies each span the command ends, upstream HTTP calls included.
- `TrailLogProcessor` copies each structlog line at info level and above.
- `Command.run` notes what ran, its parse, timing, outcome, OTel trace id and failure.
- The platform names each reply it sent. WhatsApp replies get their id from the core
  (`message_id` in the reply payload, in Baileys' `3EB0…` format), so the core knows it
  before the gateway sends. Discord and Telegram return the id from the send call.

On close the trail becomes one zlib-compressed record in Redis under
`execution:<uuid>`, with a pointer `execution_reply:<platform>:<chat>:<message id>` per
reply. Both expire after `ExecutionStore.RETENTION_SECONDS` (3 days). The Redis plan's
30 MB is shared with the agent checkpointer and the inboxes, and every command writes a
record, so the retention stays short.

The capture is bounded: at most 64 spans and 64 log lines per command, and 1 024
entries across every open command (`TelemetryBuffer`). An entry past a cap is counted
and the issue says how many were dropped. Closing the trail releases its entries.

## Redaction

The repo is public. Every captured field goes through `TelemetryFieldPolicy`
(`bot/infrastructure/telemetry_field_policy.py`):

- A name holding a secret part (`key`, `token`, `auth`, `secret`, `pass`, `pwd`,
  `sig`, `session`, `credential`) hides its value.
- An identity name (`chat`, `sender`, `jid`, any `*_id` or `*jid`) is hashed with
  HMAC-SHA256. The key is drawn when the process starts, so a hash can't be reversed
  by enumerating phone numbers, and stays the same for every id in one record.
- An allowlisted name (`bot/data/telemetry_privacy.py`, `SAFE_FIELDS`: codes, counts,
  durations, the upstream host) shows its value, redacted, when the value is a plain
  string, number or bool. Any other object shows its type.
- Any other name is dropped. A frame argument off the list shows its type, or a
  string its length.
- URL attributes keep scheme, host and path only.

Free text is redacted by `TelemetryRedactor`: URL userinfo, query strings and fragments
are dropped, Telegram bot tokens, bearer credentials and provider key prefixes are
hidden, and JIDs and phone numbers are hashed. Span status descriptions are never
copied. A failure keeps its type, a 120-character message (a `BotError` shows the
user's reply, not its detail) and a stack of `file:line in function` frames, without
source lines or chained messages.

The user's command text and args are kept on purpose, redacted, because a dev chose to
file the issue and they reproduce the bug. The dev's description goes through the same
redaction. An `@name` in any text gets a zero-width space so it notifies nobody.

Only four kinds of free text reach an issue: the command text and args, the marked
reply, the dev's description and the 120-character exception message. Everything else
is a code, a count, a duration, an allowlisted name's plain value, or a type and
length. The free-text redaction is best effort: patterns can't know every credential
format. The dev who files a report reads the issue right after, and edits or deletes it
if something slipped through.

## What the issue holds

- **Report**: the dev's description and the marked reply.
- **Command**: name, text, flags, options, args, platform and chat type, hashed chat
  and sender, message id, correlation id, attempt, timestamps, duration and outcome.
- **Failure**: type, message, the deepest bot frame with its arguments, the folded
  stack and a Sentry search by the `correlation_id` tag.
- **Telemetry**: the trace id with Tempo and Loki links, the span tree with total and
  self time and the upstream host, method and status, the log lines, and the host's
  RSS, event-loop lag and deliveries in flight.

Labels: `bug`, `from-bot`, plus `external-api` when the outcome is `external_error`.

Filing is guarded by `IssueFilings`: a Redis claim keyed by the `,bug` message, so a
broker redelivery (ADR 0001) files one issue.

## Settings

| Setting | Use |
|---|---|
| `GITHUB_ISSUES_TOKEN` | fine-grained token with Issues: write on this repo only. Empty disables `,bug`. A runner's own `GITHUB_TOKEN` never enables it |
| `GITHUB_REPOSITORY` | `owner/repo` the issues go to, `sandrosmarzaro/resenhazord2` by default |
| `GRAFANA_URL` | Grafana stack URL for the Tempo and Loki links. Empty leaves them out |
| `SENTRY_ORG` | Sentry org slug for the event search link. Empty leaves it out |

`REDIS_URL` must be set for records to exist at all.
