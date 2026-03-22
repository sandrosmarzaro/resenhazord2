# Response Formatting Conventions

Guidelines for formatting bot responses (text messages and image captions). Apply to all
new commands and when editing existing command responses.

## Caption Structure

Build captions as a list of lines joined with `'\n'.join()`. Use empty strings for blank
lines between major sections.

```
*Title* — Type            ← bold name, optional type/category
Stats line                 ← emoji-prefixed stats on one line
                           ← blank line
Metadata lines             ← secondary info
                           ← blank line
> Description text         ← quote block for long-form text
```

### Title Line

Always bold the name. Append type/category with ` — ` dash when the item has a type:

```
*Dark Magician* — Normal Monster
*Lightning Bolt* — Instant
*Fireball*
```

### Stats

Join stats on a single line with 3-space separator (`'   '.join()`):

```
⚔️ ATK: 2500   🛡️ DEF: 2100   ⭐ Lv. 7
💎 8   ⚔️ 8   ❤️ 8
💎 Common   {R}
```

### Section Spacing

- **Between major sections** (title → stats → metadata → description): blank line (`\n\n`)
- **Within a section** (multiple stat lines, metadata lines): single `\n`

### Descriptions and Long Text

Always use quote blocks (`>`) for:

- Card text / abilities
- Movie/anime synopses
- Flavor text
- Religious verses
- Horoscope text
- Any prose paragraph

```python
lines.append(f'\n> {description}')
```

### Metadata Lines

Use emoji prefix for each metadata item. One item per line or joined with `'   '`:

```
🌑 DARK   Spellcaster
📅 2024
⭐ 8.5/10
```

## Text-Only Responses

### Simple Results

Single line with emoji at end:

```
Aqui está sua rolada: 17 🎲
```

### Structured Results

Same rules as captions — bold title, blank line separation, quote blocks for prose:

```
♈ *Áries* (21/03 - 19/04)

> Today brings unexpected opportunities...
```

### Usage/Help Messages

Show command syntax, then list options:

```
Uso: ,horóscopo <signo>

♈ Áries (21/03 - 19/04)
♉ Touro (20/04 - 20/05)
...
```

## Error Messages

Short and informal. Emoji at end. No stack traces or technical details:

```
Não consegui buscar essa carta. Tente de novo! 🤷‍♂️
Essa carta não tem imagem. Tente novamente.
```

## Booster/Grid Captions

Use numbered bold labels, double-spaced:

```python
'\n\n'.join(f'*{i + 1}.* {item.label}' for i, item in enumerate(items))
```

## Caption Builder Pattern

Extract a `_build_caption(card: dict) -> str` static method. Build lines as a list:

```python
@staticmethod
def _build_caption(card: dict) -> str:
    lines: list[str] = [f'*{card["name"]}* — {card.get("type", "")}']

    stats: list[str] = []
    if card.get('attack') is not None:
        stats.append(f'⚔️ {card["attack"]}')
    if stats:
        lines.append('   '.join(stats))

    text = card.get('text', '')
    if text:
        lines.append(f'\n> {text}')

    return '\n'.join(lines)
```
