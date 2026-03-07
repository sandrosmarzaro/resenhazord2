# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Resenhazord2 is a WhatsApp chatbot built with TypeScript on the Bun runtime. It uses Baileys (@whiskeysockets/baileys) for WhatsApp Web integration and responds to commands prefixed with `,` (comma).

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
6. Messages are sent back via the Baileys socket

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

### CommandConfig (`src/types/commandConfig.ts`)

| Field         | Type           | Description                                                                          |
| ------------- | -------------- | ------------------------------------------------------------------------------------ |
| `name`        | `string`       | Primary command name. Diacritics auto-handled (e.g., `'pokémon'` matches `,pokemon`) |
| `aliases`     | `string[]?`    | Alternative names (e.g., `['série']` for FilmeSerieCommand)                          |
| `flags`       | `string[]?`    | Boolean on/off toggles. `dm` and `show` are handled by the base class                |
| `options`     | `OptionDef[]?` | Named parameters that select one value from a set or match a pattern                 |
| `args`        | `ArgType?`     | `None` (default), `Required`, or `Optional` — free-text after command                |
| `argsPattern` | `RegExp?`      | Validation regex for args (e.g., `/^(?:@\d+\s*)*$/`)                                 |
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
4. Set `viewOnce: true` if returning media (base class handles `show` flag)
5. Use `jid: data.key.remoteJid!` always (base class handles `dm` flag)
6. Import and register it in `CommandFactory`'s constructor
7. Create `tests/unit/commands/FooCommand.test.ts`

### Key Types

- `CommandData` — extends `WAMessage` with `text: string` and `expiration: number | undefined`
- `Message` — `{ jid, content: AnyMessageContent, options? }`
- `CommandConfig` — declarative config: name, aliases, flags, options, args, groupOnly
- `ParsedCommand` — parser output: commandName, flags (`Set`), options (`Map`), rest (`string`)

### Singletons

`CommandFactory`, `MongoDBConnection`, `AxiosClient` all use the singleton pattern.

## Code Conventions

- **Runtime**: Bun (not Node.js)
- **Modules**: ES modules with `.js` extensions in imports (even for `.ts` files)
- **File naming**: PascalCase for classes (e.g., `OiCommand.ts`, `GetTextMessage.ts`)
- **Exports**: Default exports for class files, named exports for data files
- **Formatting**: Prettier — single quotes, semicolons, 2-space indent, 100 char width
- **Commit messages**: Conventional commits (`feat:`, `fix:`, `test:`, `refactor:`, `style:`, `ci:`, `chore:`)

## Testing

- **Framework**: Vitest with globals enabled
- **Fixtures**: `tests/fixtures/index.js` provides `GroupCommandData` and `PrivateCommandData` factories (using Fishery)
- **Setup**: `tests/setup.ts` mocks external dependencies (google-tts-api, Gemini, sharp, pino, mongodb)
- **Pattern**: Tests instantiate the command directly, use factories for `CommandData`, and assert on the returned `Message[]`

## Environment

Requires a `.env` file (see `.env.example`) with keys for: WhatsApp JIDs, Gemini API, MongoDB URI, TMDB, and other service credentials.
