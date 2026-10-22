"""Replies to the agent's "Você quis dizer ,x?" confirmation, already normalized
(lowercase, no accents, no ASCII punctuation)."""

CONFIRM_REPLIES = frozenset(
    {
        'sim',
        's',
        'ss',
        'isso',
        'isso mesmo',
        'isso ai',
        'pode',
        'pode ser',
        'claro',
        'bora',
        'quero',
        'exato',
        'certo',
        'ok',
        'okay',
        'yes',
        'y',
        '👍',
        '✅',
    }
)
DENY_REPLIES = frozenset(
    {'nao', 'n', 'nn', 'errado', 'negativo', 'nope', 'no', 'nao e isso', 'nao quero', '👎', '❌'}
)
ASK_AGAIN_QUESTION = 'O que você queria?'
# Skin-tone modifiers (U+1F3FB..U+1F3FF) and the emoji variation selector: '👍🏽' is '👍'.
EMOJI_MODIFIERS = frozenset({*map(chr, range(0x1F3FB, 0x1F400)), '\ufe0f'})
