import html
import re
from typing import ClassVar


class WhatsAppHtmlFormatter:
    BOLD_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'\*([^*\n]+?)\*')
    ITALIC_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r'(?<![a-zA-Z0-9])_([^_\n]+?)_(?![a-zA-Z0-9])'
    )
    BULLET_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'(^|\n)- (?=\S)')
    BULLET_REPLACEMENT: ClassVar[str] = '\\1• '
    BLOCKQUOTE_PREFIX: ClassVar[str] = '&gt; '

    @classmethod
    def to_html(cls, text: str) -> str:
        if not text:
            return text
        escaped = html.escape(text, quote=False)
        with_bullets = cls.BULLET_PATTERN.sub(cls.BULLET_REPLACEMENT, escaped)
        with_blockquotes = cls._apply_blockquotes(with_bullets)
        with_bold = cls.BOLD_PATTERN.sub(r'<b>\1</b>', with_blockquotes)
        return cls.ITALIC_PATTERN.sub(r'<i>\1</i>', with_bold)

    @classmethod
    def _apply_blockquotes(cls, text: str) -> str:
        if cls.BLOCKQUOTE_PREFIX not in text:
            return text
        out: list[str] = []
        buffer: list[str] = []
        for line in text.split('\n'):
            if line.startswith(cls.BLOCKQUOTE_PREFIX):
                buffer.append(line.removeprefix(cls.BLOCKQUOTE_PREFIX))
                continue
            cls._flush(out, buffer)
            out.append(line)
        cls._flush(out, buffer)
        return '\n'.join(out)

    @staticmethod
    def _flush(out: list[str], buffer: list[str]) -> None:
        if not buffer:
            return
        joined = '\n'.join(buffer)
        out.append(f'<blockquote>{joined}</blockquote>')
        buffer.clear()
