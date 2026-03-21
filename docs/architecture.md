# Architecture

## Message Flow

1. Baileys socket receives a message → `messages.upsert` event
2. `MessageUpsertEvent` filters messages (only specific group JIDs)
3. `CommandHandler.run(message)` extracts text and finds a matching command
4. `CommandFactory.getStrategy(text)` iterates registered commands, matching via regex
5. The matched `Command.run(data)` executes and returns `Message[]`
6. Messages are sent back via the WhatsApp adapter

## Command System

Every command extends the abstract `Command` class (`bot/domain/commands/base.py`):

- `config: CommandConfig` — declarative config for matching and parsing
- `menu_description: str` — description shown in the `,menu` command
- `execute(data: CommandData, parsed: ParsedCommand) -> list[BotMessage]` — command logic

The base `Command.run()` is a template method that:

1. Checks `group_only` and returns an error if used in a private chat
2. Parses the message text via `CommandParser` into a `ParsedCommand`
3. Calls the subclass `execute()` method
4. Applies `dm` and `show` flags centrally (commands don't handle these)

`CommandParser` (`bot/domain/parsers/command_parser.py`) auto-generates a regex from the config for `matches()`, and tokenizes the text for `parse()`. Diacritics in names/flags/options are replaced with `.` in the regex.

`CommandRegistry` (`bot/application/command_registry.py`) is a singleton that holds all command instances and selects the first match.

The TS gateway mirrors the parser (`gateway/src/parsers/CommandParser.ts`) for initial command matching before forwarding to Python.

## Ports & Adapters

`WhatsAppPort` (`gateway/src/ports/WhatsAppPort.ts`) abstracts WhatsApp operations behind an interface (sendMessage, groupMetadata, groupParticipantsUpdate, onWhatsApp, updateMediaMessage, etc.).

`BaileysAdapter` (`gateway/src/adapters/BaileysAdapter.ts`) implements `WhatsAppPort` by wrapping the Baileys `WASocket`.

`Resenhazord2.adapter` (static, public) is the entry point; `socket` is private. On reconnection, a new adapter is created.

Commands that need WhatsApp operations receive `WhatsAppPort` via constructor injection. Python commands access WhatsApp via `self._whatsapp` (the `WhatsAppWsClient` that delegates to TS over WebSocket).

## Media Download

Media is downloaded proactively by the TS gateway when a message arrives. The bytes are sent as a binary WebSocket frame before the command JSON. Python commands access media via `self._get_media(data)` which returns the proactive buffer or falls back to a `wa_call download_media` round-trip.

## Reply Builder

`Reply` (`bot/domain/builders/reply.py`) provides a fluent API for building `BotMessage` objects:

```python
Reply.to(data).text('hello')
Reply.to(data).image(url, caption)
```

`Reply.to(data)` captures the `CommandData` context. Terminal methods return a `Message`:

- `text(text)` — plain text
- `textWith(text, mentions)` — text with mentions
- `image(url, caption?)` — image from URL (viewOnce: true)
- `imageBuffer(buffer, caption?)` — image from buffer (viewOnce: true)
- `video(url, caption?)` — video from URL (viewOnce: true)
- `audio(url)` — audio from URL
- `sticker(buffer)` — sticker from buffer
- `raw(content)` — arbitrary content

Automatically sets `jid`, `quoted`, and `ephemeralExpiration` from the `CommandData`. Media methods default to `viewOnce: true` (base class handles the `show` flag to override this).

## CommandConfig

| Field         | Type           | Description                                                                          |
| ------------- | -------------- | ------------------------------------------------------------------------------------ |
| `name`        | `string`       | Primary command name. Diacritics auto-handled (e.g., `'pokémon'` matches `,pokemon`) |
| `aliases`     | `string[]?`    | Alternative names (e.g., `['série']` for FilmeSerieCommand)                          |
| `flags`       | `string[]?`    | Boolean on/off toggles. `dm` and `show` are handled by the base class                |
| `options`     | `OptionDef[]?` | Named parameters that select one value from a set or match a pattern                 |
| `args`        | `ArgType?`     | `None` (default), `Required`, or `Optional` — free-text after command                |
| `argsPattern` | `RegExp?`      | Validation regex for args (e.g., `/^(?:@\d+(?:\s+@\d+)*)?$/`)                        |
| `groupOnly`   | `boolean?`     | Restricts command to group chats (handled by base class)                             |

**Flags** = boolean toggles (present or absent): `,pokemon team`, `,musica free`
**Options** = select one value from alternatives: `,img hd flux-pro`, `,biblia pt nvi`

Use `parsed.flags.has('flag')` for flags, `parsed.options.get('name')` for options, and `parsed.rest` for free-text args.

**Base class auto-handles:**

- `groupOnly` — returns error message for private chats
- `dm` flag — redirects response to sender's DM
- `show` flag — sets `viewOnce: false` (commands set `viewOnce: true` by default)

## Adding a New Command

1. Create `bot/domain/commands/foo.py` extending `Command`
2. Define `config: CommandConfig` with appropriate name, flags, options, args
3. Implement `execute(data, parsed)` — use `parsed.flags`, `parsed.options`, `parsed.rest`
4. Use `Reply.to(data)` to build responses (media methods default to `view_once=True`)
5. If the command needs WhatsApp operations, accept `WhatsAppPort` in constructor
6. Register it in `bot/application/register_commands.py`
7. Create `tests/unit/commands/test_foo.py`

## Key Types

- `CommandData` (`bot/domain/models/command_data.py`) — platform-agnostic command data with text, jid, media info, etc.
- `BotMessage` (`bot/domain/models/message.py`) — response message with content and metadata
- `CommandConfig` (`bot/domain/commands/base.py`) — declarative config: name, aliases, flags, options, args, group_only
- `ParsedCommand` (`bot/domain/commands/base.py`) — parser output: command_name, flags (`set`), options (`dict`), rest (`str`)

## Error Handling

Commands can raise `BotError` subclasses (`bot/domain/exceptions.py`) to send user-facing error messages:

- `CommandError` — general command execution errors
- `MediaNotFoundError` — no media attached when expected
- `ValidationError` — invalid input
- `ExternalServiceError` — external API failures
- `DownloadError` — yt-dlp/download failures

The `WebSocketHandler` catches `BotError` and converts `error.user_message` into a reply. Unexpected exceptions are logged and sent as error JSON.

## Group Metadata Cache

`gateway/src/cache/` implements a layered cache for `GroupMetadata` using the decorator pattern:

- `CachePort<V>` (`gateway/src/cache/CachePort.ts`) — generic interface: `get(key): Promise<V | undefined>`, `set(key, value): Promise<void>`
- `MemoryGroupMetadataCache` — `Map`-backed, always available, no TTL
- `RedisGroupMetadataCache` — wraps `@upstash/redis`; TTL = 3600 s; `Redis` injected via constructor
- `FallbackGroupMetadataCache` — decorator: `get` tries primary → falls back on miss or error; `set` writes fallback first (reliable), then primary (errors swallowed)
- `gateway/src/cache/index.ts` — factory singleton: if `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` are set, returns `FallbackGroupMetadataCache(Redis, Memory)`; otherwise `MemoryGroupMetadataCache`

## Singletons

`CommandFactory`, `MongoDBConnection`, `AxiosClient` all use the singleton pattern. `CommandFactory` has `reset()` for reconnection (new adapter → new factory instance).

**Always use existing singletons** — never instantiate `axios`, `new MongoClient()`, or similar clients directly. Use `AxiosClient.get()` / `AxiosClient.post()` / `AxiosClient.getBuffer()` for all HTTP requests. These singletons provide centralized retry logic, timeout defaults, and Sentry breadcrumbs.
