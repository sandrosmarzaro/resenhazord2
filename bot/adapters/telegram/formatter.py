import html
import re
from typing import Final

_BOLD_PATTERN: Final[re.Pattern[str]] = re.compile(r'\*([^*\n]+?)\*')
_ITALIC_PATTERN: Final[re.Pattern[str]] = re.compile(r'(?<![a-zA-Z0-9])_([^_\n]+?)_(?![a-zA-Z0-9])')
_BLOCKQUOTE_PREFIX: Final[str] = '&gt; '


def whatsapp_to_html(text: str) -> str:
    if not text:
        return text
    escaped = html.escape(text, quote=False)
    with_blockquotes = _apply_blockquotes(escaped)
    with_bold = _BOLD_PATTERN.sub(r'<b>\1</b>', with_blockquotes)
    return _ITALIC_PATTERN.sub(r'<i>\1</i>', with_bold)


def _apply_blockquotes(text: str) -> str:
    if _BLOCKQUOTE_PREFIX not in text:
        return text
    out: list[str] = []
    buffer: list[str] = []
    for line in text.split('\n'):
        if line.startswith(_BLOCKQUOTE_PREFIX):
            buffer.append(line.removeprefix(_BLOCKQUOTE_PREFIX))
            continue
        _flush(out, buffer)
        out.append(line)
    _flush(out, buffer)
    return '\n'.join(out)


def _flush(out: list[str], buffer: list[str]) -> None:
    if not buffer:
        return
    joined = '\n'.join(buffer)
    out.append(f'<blockquote>{joined}</blockquote>')
    buffer.clear()
