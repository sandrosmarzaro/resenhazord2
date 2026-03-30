import re
from urllib.parse import urlencode

from bot.data.languages import LANGUAGES
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    ArgType,
    Category,
    Command,
    CommandConfig,
    Flag,
    OptionDef,
    ParsedCommand,
    Platform,
)
from bot.domain.exceptions import ValidationError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class AudioCommand(Command):
    TTS_HOST = 'https://translate.google.com'
    MAX_CHUNK_LENGTH = 200
    DEFAULT_LANGUAGE = 'pt-br'
    SPLIT_PUNCTUATION = '.!?;:'
    SPACE_AND_PUNCT_RE = re.compile(r'[\s\uFEFF\xA0!"#$%&\'()*+,\-./:;<=>?@\[\]^_`{|}~.!?;:]')

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='áudio',
            options=[OptionDef(name='lang', pattern=r'[A-Za-z]{2}-[A-Za-z]{2}')],
            flags=[Flag.DM],
            args=ArgType.OPTIONAL,
            category=Category.DOWNLOAD,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Converta texto em audio usando a voz do Google, podendo trocar a língua.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        language = (parsed.options.get('lang') or self.DEFAULT_LANGUAGE).lower()
        if language not in LANGUAGES:
            return [Reply.to(data).text('Burro burro! O idioma 🏳️‍🌈 não existe!')]

        text = parsed.rest.strip() or (data.quoted_text or '').strip()
        if not text:
            return [Reply.to(data).text('Burro burro! Cadê o texto? 🤨')]

        chunks = self._split_long_text(text)
        urls = [
            self._build_tts_url(chunk, language, i, len(chunks)) for i, chunk in enumerate(chunks)
        ]

        if len(text) <= self.MAX_CHUNK_LENGTH:
            return [Reply.to(data).audio(urls[0], mimetype='audio/mpeg')]

        return [Reply.to(data).audio(url, mimetype='audio/mpeg') for url in urls]

    def _build_tts_url(self, text: str, lang: str, idx: int, total: int) -> str:
        params = urlencode(
            {
                'ie': 'UTF-8',
                'q': text,
                'tl': lang,
                'total': total,
                'idx': idx,
                'textlen': len(text),
                'client': 'tw-ob',
                'prev': 'input',
                'ttsspeed': 1,
            }
        )
        return f'{self.TTS_HOST}/translate_tts?{params}'

    def _split_long_text(self, text: str) -> list[str]:
        result: list[str] = []
        start = 0

        while start < len(text):
            if len(text) - start <= self.MAX_CHUNK_LENGTH:
                result.append(text[start:])
                break

            end = start + self.MAX_CHUNK_LENGTH - 1

            if self._is_space_or_punct(text, end) or (
                end + 1 < len(text) and self._is_space_or_punct(text, end + 1)
            ):
                result.append(text[start : end + 1])
                start = end + 1
                continue

            split_pos = self._last_space_or_punct(text, start, end)
            if split_pos == -1:
                msg = f'Word too long to split: {text[start : start + self.MAX_CHUNK_LENGTH]}...'
                raise ValidationError(msg)

            result.append(text[start : split_pos + 1])
            start = split_pos + 1

        return result

    def _is_space_or_punct(self, text: str, index: int) -> bool:
        return bool(self.SPACE_AND_PUNCT_RE.match(text[index]))

    @staticmethod
    def _last_space_or_punct(text: str, left: int, right: int) -> int:
        for i in range(right, left - 1, -1):
            if AudioCommand.SPACE_AND_PUNCT_RE.match(text[i]):
                return i
        return -1
