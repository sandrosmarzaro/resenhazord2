# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Resenhazord2 is a WhatsApp chatbot built with TypeScript on the Bun runtime. It uses Baileys (@whiskeysockets/baileys) for WhatsApp Web integration and responds to commands prefixed with `,` (comma).

## MCP Tools

Use the **context7** MCP (`mcp__context7__resolve-library-id` + `mcp__context7__query-docs`) to fetch up-to-date documentation for any library (e.g., `@whiskeysockets/baileys`, `vitest`, `@upstash/redis`).

## Common Commands

```bash
bun start              # Run the bot
bun test               # Run tests (vitest in watch mode)
bun test:run           # Run tests once
bun test:unit          # Run only unit tests
bun vitest run tests/unit/commands/FooCommand.test.ts  # Run a single test file
bun lint               # ESLint check
bun lint:fix           # ESLint auto-fix
bun typecheck          # TypeScript type checking (tsc --noEmit)
bun format             # Prettier format
bun format:check       # Prettier check
```

Pre-push hook runs: lint, typecheck, format:check.

## Architecture

### Message Flow

1. Baileys socket receives a message → `messages.upsert` event
2. `MessageUpsertEvent` filters messages (only specific group JIDs)
3. `CommandHandler.run(message)` extracts text and finds a matching command
4. `CommandFactory.getStrategy(text)` iterates registered commands, matching via regex
5. The matched `Command.run(data)` executes and returns `Message[]`
6. Messages are sent back via the WhatsApp adapter

### Command System

Every command extends the abstract `Command` class (`src/commands/Command.ts`):

- `config: CommandConfig` — declarative config for matching and parsing (see below)
- `menuDescription: string` — description shown in the `,menu` command
- `execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]>` — command logic

The base `Command.run()` is a template method that:

1. Checks `groupOnly` and returns an error if used in a private chat
2. Parses the message text via `CommandParser` into a `ParsedCommand`
3. Calls the subclass `execute()` method
4. Applies `dm` and `show` flags centrally (commands don't handle these)

`CommandParser` (`src/parsers/CommandParser.ts`) auto-generates a regex from the config for `matches()`, and tokenizes the text for `parse()`. Diacritics in names/flags/options are replaced with `.` in the regex.

`CommandFactory` (`src/factories/CommandFactory.ts`) is a singleton that holds all command instances and selects the first match via `getStrategy(text)`.

### Ports & Adapters

`WhatsAppPort` (`src/ports/WhatsAppPort.ts`) abstracts WhatsApp operations behind an interface (sendMessage, groupMetadata, groupParticipantsUpdate, onWhatsApp, updateMediaMessage, etc.).

`BaileysAdapter` (`src/adapters/BaileysAdapter.ts`) implements `WhatsAppPort` by wrapping the Baileys `WASocket`.

`Resenhazord2.adapter` (static, public) is the entry point; `socket` is private. On reconnection, a new adapter is created.

Commands that need WhatsApp operations receive `WhatsAppPort` via constructor injection (`this.whatsapp`). 7 commands use it: AddCommand, AdmCommand, AllCommand, BanCommand, StickerCommand, ScarraCommand, DriveCommand.

### Reply Builder

`Reply` (`src/builders/Reply.ts`) provides a fluent API for building `Message` objects:

```ts
Reply.to(data).text('hello');
Reply.to(data).image(url, caption);
```

`Reply.to(data)` captures the `CommandData` context. Terminal methods return a `Message`:

- `text(text)` — plain text
- `textWith(text, mentions)` — text with mentions
- `image(url, caption?)` — image from URL (viewOnce: true)
- `imageBuffer(buffer, caption?)` — image from buffer (viewOnce: true)
- `video(url, caption?)` — video from URL (viewOnce: true)
- `audio(url)` — audio from URL
- `sticker(buffer)` — sticker from buffer
- `raw(content)` — arbitrary `AnyMessageContent`

Automatically sets `jid`, `quoted`, and `ephemeralExpiration` from the `CommandData`. Media methods default to `viewOnce: true` (base class handles the `show` flag to override this).

### CommandConfig (`src/types/commandConfig.ts`)

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

### Adding a New Command

1. Create `src/commands/FooCommand.ts` extending `Command`
2. Define `config: CommandConfig` with appropriate name, flags, options, args
3. Implement `execute(data, parsed)` — use `parsed.flags`, `parsed.options`, `parsed.rest`
4. Use `Reply.to(data)` to build responses (media methods default to `viewOnce: true`)
5. If the command needs WhatsApp operations (group metadata, etc.), accept `WhatsAppPort` in constructor and register with it in `CommandFactory`
6. Import and register it in `CommandFactory`'s constructor
7. Create `tests/unit/commands/FooCommand.test.ts`

### Key Types

- `CommandData` — extends `WAMessage` with `text: string` and `expiration: number | undefined`
- `Message` — `{ jid, content: AnyMessageContent, options? }`
- `CommandConfig` — declarative config: name, aliases, flags, options, args, groupOnly
- `ParsedCommand` — parser output: commandName, flags (`Set`), options (`Map`), rest (`string`)

### Group Metadata Cache

`src/cache/` implements a layered cache for `GroupMetadata` using the decorator pattern:

- `CachePort<V>` (`src/cache/CachePort.ts`) — generic interface: `get(key): Promise<V | undefined>`, `set(key, value): Promise<void>`
- `MemoryGroupMetadataCache` — `Map`-backed, always available, no TTL
- `RedisGroupMetadataCache` — wraps `@upstash/redis`; TTL = 3600 s; `Redis` injected via constructor
- `FallbackGroupMetadataCache` — decorator: `get` tries primary → falls back on miss or error; `set` writes fallback first (reliable), then primary (errors swallowed)
- `src/cache/index.ts` — factory singleton: if `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` are set, returns `FallbackGroupMetadataCache(Redis, Memory)`; otherwise `MemoryGroupMetadataCache`

Populated in `Resenhazord2` via `groups.upsert` and `group-participants.update` events.

### Singletons

`CommandFactory`, `MongoDBConnection`, `AxiosClient` all use the singleton pattern. `CommandFactory` has `reset()` for reconnection (new adapter → new factory instance).

**Always use existing singletons** — never instantiate `axios`, `new MongoClient()`, or similar clients directly. Use `AxiosClient.get()` / `AxiosClient.post()` / `AxiosClient.getBuffer()` for all HTTP requests. These singletons provide centralized retry logic, timeout defaults, and Sentry breadcrumbs. Creating new instances bypasses these guarantees.

### Sentry

`src/infra/Sentry.ts` initializes `@sentry/bun`. Always import as:

```ts
import { Sentry } from './src/infra/Sentry.js';
```

**Structured Logs** — `Sentry.logger.<level>()` with `fmt` tagged template for interpolation:

```ts
Sentry.logger.warn(Sentry.logger.fmt`Cache miss for key ${key}: ${error}`);
```

Levels (low → high): `trace` · `debug` · `info` · `warn` · `error` · `fatal`

**Error capture** — always include `extra` context to aid debugging:

```ts
Sentry.captureException(error, { extra: { method: 'create', chatJid } });
Sentry.captureMessage('Bot logged out', 'warning'); // levels: debug|info|log|warning|error|fatal
```

**Breadcrumbs** — trail of events before an error occurs:

```ts
Sentry.addBreadcrumb({ category: 'command', message: 'Executing FooCommand', level: 'info' });
```

**Scoped context** — tag errors with structured metadata:

```ts
Sentry.withScope((scope) => {
  scope.setTag('command', command.constructor.name);
  scope.setExtra('jid', jid);
  Sentry.captureException(error);
});
```

**Traces** — `tracesSampleRate: 0.1` (10%) configured in `Sentry.ts`; no manual spans currently.

**Sentry CLI** — uses `SENTRY_TOKEN` from `.env` for releases and source maps:

```bash
SENTRY_AUTH_TOKEN=$SENTRY_TOKEN sentry-cli releases ...
SENTRY_AUTH_TOKEN=$SENTRY_TOKEN sentry-cli sourcemaps upload ...
```

### Querying Issues

Use `SENTRY_TOKEN` from `.env` to query issues via the REST API without opening the web UI.

**List recent unresolved issues:**

```bash
curl -s \
  -H "Authorization: Bearer $SENTRY_TOKEN" \
  "https://sentry.io/api/0/projects/smarzaro/resenhazord2/issues/?query=is:unresolved&limit=10" \
  | python3 -c "import json,sys; [print(i['id'], i['shortId'], i['title']) for i in json.load(sys.stdin)]"
```

**Fetch a specific issue (title, culprit, tags):**

```bash
curl -s \
  -H "Authorization: Bearer $SENTRY_TOKEN" \
  "https://sentry.io/api/0/issues/<ISSUE_ID>/" \
  | python3 -m json.tool
```

**Get the latest event with full stack trace:**

```bash
curl -s \
  -H "Authorization: Bearer $SENTRY_TOKEN" \
  "https://sentry.io/api/0/issues/<ISSUE_ID>/events/latest/" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for entry in d.get('entries', []):
    if entry.get('type') == 'exception':
        for exc in entry['data']['values']:
            print(exc.get('type'), exc.get('value'))
            for f in exc['stacktrace']['frames']:
                if f.get('inApp'):
                    print(f'  {f[\"filename\"]}:{f[\"lineNo\"]} in {f[\"function\"]}')
"
```

Replace `<ISSUE_ID>` with the numeric ID from the issue URL (e.g. `7333954839`) or use `shortId` like `RESENHAZORD2-9`.

**Test mock** — all Sentry APIs are mocked in `tests/setup.ts`. When adding new `Sentry.logger` usage,
ensure `fmt` is mocked as a tagged template literal:

```ts
fmt: (strings: TemplateStringsArray, ...values: unknown[]) =>
  String.raw({ raw: strings }, ...values);
```

## Code Conventions

- **Runtime**: Bun (not Node.js)
- **Modules**: ES modules with `.js` extensions in imports (even for `.ts` files)
- **File naming**: PascalCase for classes (e.g., `OiCommand.ts`, `GetTextMessage.ts`)
- **Exports**: Default exports for class files, named exports for data files
- **Data files**: Large lookup tables, emoji maps, and static datasets belong in `src/data/` (e.g., `bichoAnimalEmojis.ts`, `pokemonTypeEmojis.ts`). Do not define big mappings inline in service or command files.
- **No module-level variables**: Avoid `const FOO = ...` at module scope in service/command files. Use `private static readonly` class attributes for constants that belong to a class.
- **Formatting**: Prettier — single quotes, semicolons, 2-space indent, 100 char width
- **Commit messages**: Conventional commits (`feat:`, `fix:`, `test:`, `refactor:`, `style:`, `ci:`, `chore:`)

## Testing

- **Framework**: Vitest with globals enabled
- **Fixtures**: `tests/fixtures/index.js` provides `GroupCommandData` and `PrivateCommandData` factories (using Fishery)
- **Setup**: `tests/setup.ts` mocks external dependencies (google-tts-api, Gemini, sharp, pino, mongodb, @sentry/bun)
- **Pattern**: Tests instantiate the command directly, use factories for `CommandData`, and assert on the returned `Message[]`
- **WhatsApp mock**: `createMockWhatsAppPort()` from `tests/fixtures/factories/MockWhatsAppPort.ts` provides a mock `WhatsAppPort` for commands that need it (constructor-injected)

## AI Guidelines

- Always run `bun format` after editing code and verify no lines exceed 100 characters
- Always run `bun typecheck` after changes and distinguish between pre-existing vs newly introduced errors
- Always run `bun test:run` after changes and verify all previously passing tests still pass
- Always ask/talk about of implementation of code, which design use pattern/library/algorithms/architecture/design system, suggesting alternatives(prefer free ways) with pros and cons for each, etc. To rest any debut of how make the instructions.
- When adding fields to object literals in config blocks, prefer multi-line formatting if the single-line form would exceed 100 chars

## External API Integration

1. **Test APIs first** — curl endpoints before implementing to check response format, latency, and payload size
2. **Read API docs fully** — look for simpler endpoints (e.g., `/random/card` instead of multi-step fetch), recommended formats (webp vs png), and asset URL construction rules
3. **Pre-download media as buffers** — use `AxiosClient.getBuffer()` + `Reply.to(data).imageBuffer()` so download errors are caught inside the command's try-catch, not in `sendMessages()` which only has the generic CommandHandler error handler
4. **Disable retries for slow APIs** — pass `retries: 0` in config; default 3 retries with exponential backoff silently multiply latency
5. **Prefer small formats** — use webp over png for images (can be 10x+ smaller); check API docs for recommended formats
6. **Set realistic timeouts** — consider production server latency, not local; production servers may have higher latency to external APIs

## Security

### CommandParser — regex safety

`CommandParser.replaceDiacritics()` (`src/parsers/CommandParser.ts`) escapes ASCII regex metacharacters before replacing non-ASCII chars with `.`:

```ts
s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/[^\x00-\x7F]/g, '.');
```

This means command `name`, `aliases`, `flags`, and `options[].values` are safe to use even if they contain chars like `+`, `|`, `(`, etc. Non-ASCII chars still intentionally become `.` (matches the unaccented equivalent).

### argsPattern — avoid ReDoS

Never use nested quantifiers inside repeating groups (e.g. `(?:@\d+\s*)*`). The outer `\s*` injected by `buildRegex()` creates overlap and causes catastrophic backtracking.

**Safe pattern** — separate the whitespace outside the repeating unit:

```ts
// Bad — nested quantifiers cause ReDoS
argsPattern: /^(?:@\d+\s*)*$/;

// Good — no nested overlap
argsPattern: /^(?:@\d+(?:\s+@\d+)*)?$/;
```

The outer `?` handles the optional/empty case. `\s+` between mentions eliminates ambiguity with the surrounding `\s*` injected by the parser.

## Environment

Requires a `.env` file (see `.env.example`) with keys for: WhatsApp JIDs, Gemini API, MongoDB URI, TMDB, and other service credentials.
