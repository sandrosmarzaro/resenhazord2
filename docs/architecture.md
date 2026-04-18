# Architecture

## Project Structure

```
resenhazord2/
  bot/                           Python core — all business logic
    adapters/
      whatsapp/                  Thin Python-side port (WhatsAppPort)
      discord/                   discord.py slash-command adapter
      http/                      FastAPI app + WebSocket handler
    application/
      command_handler.py         Dispatches a parsed command
      command_registry.py        Singleton list of registered Command instances
      register_commands.py       Wires every command into the registry at startup
    data/                        Lookup tables, emoji maps, static datasets
    domain/
      builders/reply.py          Fluent Reply.to(data).text(...) API
      commands/                  46 command implementations (base.py + subclasses)
      models/                    CommandData, BotMessage, content types
      parsers/command_parser.py  Regex + tokenizer generated from CommandConfig
      services/                  Shared business logic used by commands
    infrastructure/
      logging.py                 structlog + stdlib unified config
      sentry.py                  sentry_sdk.init with FastApiIntegration
      http_client.py             Singleton httpx client with retries
    ports/                       Protocols the domain depends on (DiscordPort, ...)
    main.py                      FastAPI lifespan: init Sentry, structlog, Discord task
    settings.py                  pydantic-settings from .env
  gateway/                       Bun + TypeScript — WhatsApp adapter only
    src/
      adapters/BaileysAdapter.ts Implements WhatsAppPort against a Baileys WASocket
      cache/                     Layered GroupMetadata cache (Memory + Redis)
      infra/Sentry.ts            @sentry/bun initialization
      parsers/CommandParser.ts   Mirror of Python parser for early filtering
      ports/WhatsAppPort.ts      TS interface the Python side calls via WebSocket
  docs/
  tests/                         pytest + anyio
```

## Message Flow

Two inbound platforms, one command pipeline.

### WhatsApp (via Gateway)

1. Baileys socket receives a message → `messages.upsert` event.
2. The TS gateway filters against allowed group JIDs.
3. If media is attached, gateway downloads it proactively.
4. Gateway forwards `{CommandData JSON, optional binary frame}` over WebSocket to the
   Python `WebSocketHandler`.
5. Python's `CommandHandler.handle_parsed(data)` routes the payload.

### Discord

1. `DiscordBot` (discord.py) receives an interaction for a registered slash command.
2. `DiscordInteractionAdapter` maps the interaction into a platform-agnostic
   `CommandData` (mirroring the WhatsApp shape).
3. `DiscordInteractionHandler` rewrites the Discord command name into the comma
   form (`/d20` → `',d20'`) and calls the same `CommandHandler`.

### Shared pipeline

```
CommandData ──▶ CommandRegistry.get_strategy(text) ──▶ Command.run(data)
                                                       ├─ checks group_only
                                                       ├─ parser.parse(text)
                                                       ├─ execute(data, parsed)
                                                       └─ _apply_flags (dm, show)
                                                          │
                                                          ▼
                                                    list[BotMessage]
                                                          │
                              ┌───────────────────────────┴──────────────────────────┐
                              ▼                                                      ▼
                  WebSocketHandler → gateway → Baileys        DiscordRenderer → discord.py
```

## Command System

Every command extends `Command` (`bot/domain/commands/base.py`):

- `config: CommandConfig` — declarative parsing + platform config.
- `menu_description: str` — shown by the `,menu` command.
- `execute(data, parsed) -> list[BotMessage]` — command logic.

`Command.run()` is a template method:

1. Checks `group_only` and short-circuits with a friendly error for private chats.
2. Parses the message text via `CommandParser` into a `ParsedCommand`.
3. Calls subclass `execute()`.
4. Applies `dm` and `show` flags centrally (commands don't handle these themselves).

`CommandParser` (`bot/domain/parsers/command_parser.py`) auto-generates a regex from
the config for `matches()`, and tokenizes the text for `parse()`. Diacritics in
names / flags / options are replaced with `.` so `,pokémon` and `,pokemon` both match.

`CommandRegistry` (`bot/application/command_registry.py`) is a singleton list of
registered `Command` instances and selects the first match.

The TS gateway mirrors the parser (`gateway/src/parsers/CommandParser.ts`) for
early filtering before forwarding to Python.

## Ports & Adapters

Python ports live under `bot/ports/` and `bot/adapters/whatsapp/port.py`:

- **`WhatsAppPort`** — operations the WhatsApp gateway exposes: `send_message`,
  `group_metadata`, `group_participants_update`, `on_whatsapp`,
  `update_profile_picture`, `download_media`, etc.
- **`DiscordPort`** — operations a live Discord interaction exposes:
  `send_message`, `defer`, `send_followup`, `is_deferred`.

Adapters:

- **`WhatsAppWsClient`** (`bot/adapters/whatsapp/ws_client.py`) implements
  `WhatsAppPort` by round-tripping each call over WebSocket to the TS gateway,
  which forwards to Baileys through `BaileysAdapter`.
- **`DiscordInteractionAdapter`** (`bot/adapters/discord/adapter.py`) wraps a
  `discord.Interaction` and exposes `DiscordPort`.

Commands that need WhatsApp operations accept `WhatsAppPort` in the `Command`
constructor and read it via `self.whatsapp`. `CommandRegistry.set_whatsapp(port)`
injects the port into every registered command once the WebSocket connects.

## Media Download

Media is downloaded **proactively by the TS gateway** when a WhatsApp message
arrives; the bytes are sent as a binary WebSocket frame before the command JSON.
Python commands access media via `self._get_media(data)` which returns the
proactive buffer, falling back to `whatsapp.download_media(...)` over WebSocket
if the buffer is absent.

## Reply Builder

`Reply` (`bot/domain/builders/reply.py`) is a fluent builder for `BotMessage`:

```python
from bot.domain.builders.reply import Reply

Reply.to(data).text('olá')
Reply.to(data).image(url, caption='legenda')
Reply.to(data).video_buffer(buffer, gif_playback=True)
```

`Reply.to(data)` captures `jid`, `quoted_message_id`, and `expiration` from the
`CommandData`. Terminal methods return a `BotMessage`:

- `text(text)` / `text_with(text, mentions)`
- `image(url, caption=None)` / `image_buffer(data, caption=None)`
- `video(url, caption=None)` / `video_buffer(data, caption=None, *, gif_playback=False)`
- `audio(url, mimetype='audio/mp4')` / `audio_buffer(data, mimetype='audio/mp4')`
- `sticker(data, pack='', author='')`
- `raw(content)` for arbitrary payloads

Media methods default to `view_once=True`. The base `Command._apply_flags` flips
`view_once` to `False` when the user passes the `show` flag.

## CommandConfig

```python
@dataclass(frozen=True)
class CommandConfig:
    name: str
    aliases: list[str] = []
    flags: list[str] = []
    options: list[OptionDef] = []
    args: ArgType = ArgType.NONE            # NONE | REQUIRED | OPTIONAL
    args_pattern: str | None = None         # validation regex for free-text args
    args_label: str | None = None
    scope: CommandScope = CommandScope.PUBLIC
    group_only: bool = False
    category: Category | None = None
    platforms: list[Platform] = [Platform.WHATSAPP]   # WHATSAPP and/or DISCORD
```

| Concept | Shape | Example |
|---|---|---|
| **Flag** | boolean toggle (present / absent) | `,pokemon team`, `,musica free` |
| **Option** | select one value from a set or match a pattern | `,img hd flux-pro`, `,biblia pt nvi` |
| **Args** | free-text after the command | `,google jair messias bolsonaro` |

Inside `execute`, use `parsed.flags.has('flag')`, `parsed.options.get('name')`,
and `parsed.rest`. `dm` and `show` flags are handled by the base class and never
appear in subclass code.

**Base class auto-behavior:**

- `group_only` — returns an error for private chats.
- `dm` flag — redirects response to the sender's DM.
- `show` flag — flips `view_once` off (commands default to `view_once=True`).

**Platform filter** — a command only becomes a Discord slash command when
`Platform.DISCORD` is in `config.platforms`. WhatsApp-only flags (`dm`, `show`)
are stripped from the Discord interface automatically.

## Adding a New Command

1. Create `bot/domain/commands/foo.py` extending `Command`.
2. Define `config: CommandConfig` with `name`, optional `aliases`, `flags`,
   `options`, `args`, and `platforms`.
3. Implement `execute(data, parsed)` using `parsed.flags`, `parsed.options`,
   `parsed.rest`.
4. Build responses via `Reply.to(data)` (media defaults to `view_once=True`).
5. If the command needs WhatsApp operations, read `self.whatsapp` — it's injected
   by `CommandRegistry.set_whatsapp` at startup.
6. Register in `bot/application/register_commands.py`.
7. Write `tests/unit/commands/test_foo.py` using `GroupCommandDataFactory` /
   `PrivateCommandDataFactory` and the shared `mocker`-based fixtures. See
   [.claude/rules/testing.md](../.claude/rules/testing.md).

## Key Types

- **`CommandData`** (`bot/domain/models/command_data.py`) — platform-agnostic
  command payload: text, jid, participant, media fields, `is_group`, etc.
- **`BotMessage`** (`bot/domain/models/message.py`) — response with content,
  `quoted_message_id`, `expiration`.
- **`CommandConfig`** — declarative config (above).
- **`ParsedCommand`** — parser output: `command_name`, `flags: set[str]`,
  `options: dict[str, str]`, `rest: str`.

## Error Handling

Commands raise `BotError` subclasses from `bot/domain/exceptions.py`:

- `CommandError` — general execution error.
- `MediaNotFoundError` — expected media is missing.
- `ValidationError` — invalid user input.
- `ExternalServiceError` — external API failure.
- `DownloadError` — yt-dlp or download pipeline failure.

`WebSocketHandler` (for WhatsApp) and `DiscordInteractionHandler` (for Discord)
catch `BotError` and convert `error.user_message` into a friendly reply. Unknown
exceptions are logged via `logger.exception(...)` and surfaced as generic errors.

## Group Metadata Cache (Gateway)

`gateway/src/cache/` implements a layered cache for `GroupMetadata` using the
decorator pattern. Python consumes it transparently through `WhatsAppPort`.

- `CachePort<V>` — generic `get`/`set` interface.
- `MemoryGroupMetadataCache` — `Map`-backed, always available, no TTL.
- `RedisGroupMetadataCache` — wraps `@upstash/redis`; 3600 s TTL; `Redis`
  injected via constructor.
- `FallbackGroupMetadataCache` — decorator: `get` tries primary → falls back on
  miss or error; `set` writes fallback first (reliable), then primary (errors
  swallowed).
- `gateway/src/cache/index.ts` — factory: if `UPSTASH_REDIS_REST_URL` +
  `UPSTASH_REDIS_REST_TOKEN` are set, returns `FallbackGroupMetadataCache(Redis,
  Memory)`; otherwise `MemoryGroupMetadataCache`.

## Singletons

Python: `CommandRegistry.instance()`, `MongoDBConnection`, `HttpClient`.
TypeScript: `CommandFactory`, `MongoDBConnection`, `AxiosClient`.

**Always use existing singletons.** Never instantiate `httpx.AsyncClient`,
`axios`, or `new MongoClient()` directly. Singletons centralize retry logic,
timeout defaults, and Sentry breadcrumbs.

`CommandFactory` (TS) has `reset()` for reconnection: a new Baileys adapter
creates a new factory instance.
