import random
import re

from bot.data.torah_books import TORAH_BOOKS
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
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.translator import Translator
from bot.infrastructure.http_client import HttpClient


class TorahCommand(Command):
    NOT_FOUND_MESSAGE = (
        'Versículo não encontrado. 😔\n\n'
        '📚 *Livros da Torá* 📚\n'
        '- Genesis (בראשית) — 50 capítulos\n'
        '- Exodus (שמות) — 40 capítulos\n'
        '- Leviticus (ויקרא) — 27 capítulos\n'
        '- Numbers (במדבר) — 36 capítulos\n'
        '- Deuteronomy (דברים) — 34 capítulos'
    )

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='torá',
            aliases=['torah'],
            options=[OptionDef(name='lang', values=['he', 'en', 'pt'])],
            args=ArgType.OPTIONAL,
            args_label='livro capítulo:versículo',
            flags=[Flag.DM, Flag.SHOW],
            category=Category.RANDOM,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um versículo aleatório da Torá em hebraico e português.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        rest = parsed.rest.strip()
        lang = parsed.options.get('lang')
        ref = self._parse_ref(rest)

        if ref is None:
            return [Reply.to(data).text(self.NOT_FOUND_MESSAGE)]

        url = f'https://www.sefaria.org/api/texts/{ref}?context=0'
        response = await HttpClient.get(url)
        response.raise_for_status()
        payload = response.json()

        if payload.get('error'):
            return [Reply.to(data).text(self.NOT_FOUND_MESSAGE)]

        he_raw = payload.get('he', '')
        en_raw = payload.get('text', '')
        if isinstance(he_raw, list):
            he_raw = ' '.join(he_raw)
        if isinstance(en_raw, list):
            en_raw = ' '.join(en_raw)

        if not he_raw and not en_raw:
            return [Reply.to(data).text(self.NOT_FOUND_MESSAGE)]

        return [await self._build_reply(data, payload, lang, he_raw, en_raw)]

    def _parse_ref(self, rest: str) -> str | None:
        if not rest:
            return self._random_ref()
        match = re.match(r'^(.+?)\s+(\d+):(\d+)$', rest)
        if not match:
            return None
        book_name, chapter, verse = match.group(1), match.group(2), match.group(3)
        return f'{book_name}.{chapter}.{verse}'

    @staticmethod
    def _random_ref() -> str:
        book = random.choice(TORAH_BOOKS)  # noqa: S311
        chapter_idx = random.randrange(len(book['chapters']))  # noqa: S311
        verse = random.randint(1, book['chapters'][chapter_idx])  # noqa: S311
        return f'{book["name"]}.{chapter_idx + 1}.{verse}'

    @staticmethod
    async def _build_reply(
        data: CommandData,
        payload: dict,
        lang: str | None,
        he_raw: str,
        en_raw: str,
    ) -> BotMessage:
        header = f'*{payload["ref"]} — {payload["heTitle"]}*'
        he = re.sub(r'<[^>]*>', '', he_raw).strip()
        en = re.sub(r'<[^>]*>', '', en_raw).strip()
        if lang == 'he':
            body = f'> {he}'
        elif lang == 'en':
            body = f'> {en}'
        elif lang == 'pt':
            pt = await Translator.to_pt(en)
            body = f'> {pt}'
        else:
            pt = await Translator.to_pt(en)
            body = f'> {he}\n\n> {pt}'
        return Reply.to(data).text(f'{header}\n\n{body}')
