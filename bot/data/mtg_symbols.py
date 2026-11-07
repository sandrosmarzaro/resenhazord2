import re

MTG_MANA_SYMBOLS: frozendict[str, str] = frozendict(
    {
        '{W}': '🤍',
        '{U}': '💙',
        '{B}': '🖤',
        '{R}': '❤️',
        '{G}': '💚',
        '{C}': '◇',
        '{X}': 'X',
        '{T}': '⊘',
    }
    # Numeric mana costs {0} through {20}
    | {f'{{{cost}}}': str(cost) for cost in range(21)}
)

_MANA_RE = re.compile(r'\{[^}]+\}')


def replace_mana_symbols(text: str) -> str:
    return _MANA_RE.sub(lambda m: MTG_MANA_SYMBOLS.get(m.group(), m.group()), text)
