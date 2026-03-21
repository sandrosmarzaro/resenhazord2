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
