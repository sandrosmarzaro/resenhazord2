# TypeScript rules

**Scope**: `*.ts` (primarily `gateway/`)

Things ESLint, Prettier, and `tsc --noEmit` cannot catch. The Gateway runs on Bun.

## Modules

- **ES module imports with `.js` extension**, even for `.ts` source files:
  `import { Sentry } from './src/infra/Sentry.js';`
- **Default export** for class files (one class per file, file name matches class).
  **Named exports** for data files (types, constants, fixtures).
- File name is PascalCase and equals the exported class name: `OiCommand.ts` →
  `class OiCommand`.

## Constants

- **No module-level `const FOO = ...`** in service, command, adapter, or handler
  files. Use `private static readonly` class attributes for constants that belong
  to the class.
- Lookup tables live in dedicated data files (`gateway/src/data/`), imported by
  the class that uses them.

## Types

- **No `any`** without an inline justification comment. Prefer `unknown` +
  narrowing, or define the shape.
- **No `as X`** casts without justification — prefer type guards and narrowing.

## Runtime

- Bun, not Node.js. Prefer Bun builtins (`Bun.file`, `Bun.env`) over `fs`/
  `process.env` when they exist.

## Size limits

See CLAUDE.md Code Philosophy for the canonical numbers (≤ 3 public methods / ≤ 7
attributes / ≤ 150 LOC per class, ≤ 4 params per function). Apply equally to TS.
