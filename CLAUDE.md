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

- `regexIdentifier: string` — regex pattern to match incoming messages
- `menuDescription: string` — description shown in the `,menu` command
- `run(data: CommandData): Promise<Message[]>` — command logic

`CommandFactory` (`src/factories/CommandFactory.ts`) is a singleton that holds all command instances and selects the first match via `getStrategy(text)`.

### Adding a New Command

1. Create `src/commands/FooCommand.ts` extending `Command`
2. Import and register it in `CommandFactory`'s constructor
3. Create `tests/unit/commands/FooCommand.test.ts`

### Key Types

- `CommandData` — extends `WAMessage` with `text: string` and `expiration: number | undefined`
- `Message` — `{ jid, content: AnyMessageContent, options? }`

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
