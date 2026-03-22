import re

MTG_MANA_SYMBOLS: dict[str, str] = {
    '{W}': '🤍',
    '{U}': '💙',
    '{B}': '🖤',
    '{R}': '❤️',
    '{G}': '💚',
    '{C}': '◇',
    '{X}': 'X',
    '{T}': '⊘',
}

# Add numeric mana costs {0} through {20}
for _i in range(21):
    MTG_MANA_SYMBOLS[f'{{{_i}}}'] = str(_i)

_MANA_RE = re.compile(r'\{[^}]+\}')


def replace_mana_symbols(text: str) -> str:
    return _MANA_RE.sub(lambda m: MTG_MANA_SYMBOLS.get(m.group(), m.group()), text)
