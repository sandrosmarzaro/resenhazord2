from bot.adapters.discord.music.queue import LoopMode

EMBED_COLOR = 0x1DB954

PROGRESS_BAR_FILLED = '▰'
PROGRESS_BAR_EMPTY = '▱'
PROGRESS_BAR_LENGTH = 12

LOOP_MODE_LABELS: dict[LoopMode, str] = {
    LoopMode.OFF: 'Desativado',
    LoopMode.TRACK: 'Musica',
    LoopMode.QUEUE: 'Fila',
}

LOOP_MODE_EMOJIS: dict[LoopMode, str] = {
    LoopMode.OFF: '➡️',
    LoopMode.TRACK: '🔂',
    LoopMode.QUEUE: '🔁',
}
