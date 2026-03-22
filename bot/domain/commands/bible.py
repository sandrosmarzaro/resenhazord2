import re

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, OptionDef, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient


class BibleCommand(Command):
    BASE_URL = 'https://www.abibliadigital.com.br/api'
    VERSE_PATTERN = re.compile(r'\d{1,3}\s*:\s*\d{1,3}\s*(?:-\s*\d{1,3})?')

    def __init__(self, *, biblia_token: str = '') -> None:
        super().__init__()
        self._biblia_token = biblia_token

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='bíblia',
            aliases=['bible'],
            options=[
                OptionDef(name='lang', values=['pt', 'en']),
                OptionDef(name='version', values=['nvi', 'ra', 'acf', 'kjv', 'bbe', 'apee', 'rvr']),
            ],
            args=ArgType.OPTIONAL,
            category='random',
        )

    @property
    def menu_description(self) -> str:
        return 'Comando complexo. Use *,menu biblia* para detalhes.'

    def _auth_headers(self) -> dict[str, str]:
        return {'Authorization': f'Bearer {self._biblia_token}'}

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        rest = parsed.rest.strip()
        version = parsed.options.get('version', 'nvi')
        headers = self._auth_headers()

        if not self.VERSE_PATTERN.search(rest):
            url = f'{self.BASE_URL}/verses/{version}/random'
            response = await HttpClient.get(url, headers=headers)
            response.raise_for_status()
            return [self._build_verse(data, response.json())]

        book = self.VERSE_PATTERN.sub('', rest).strip()
        if not book:
            return [Reply.to(data).text('Por favor, digite o nome do livro da bíblia... 😔')]

        chapter_match = re.search(r'(\d{1,3}):', rest)
        chapter = chapter_match.group(1) if chapter_match else ''

        abbrev = await self._resolve_abbrev(data, book)
        if isinstance(abbrev, list):
            return abbrev

        has_range = re.search(r'-\s*\d{1,3}', rest)
        if not has_range:
            number_match = re.search(r':\s*(\d{1,3})', rest)
            number = number_match.group(1) if number_match else ''
            url = f'{self.BASE_URL}/verses/{version}/{abbrev}/{chapter}/{number}'
            response = await HttpClient.get(url, headers=headers)
            response.raise_for_status()
            return [self._build_verse(data, response.json())]

        range_match = re.search(r'(\d{1,3})\s*-\s*(\d{1,3})', rest)
        start = range_match.group(1) if range_match else '1'
        end = range_match.group(2) if range_match else '1'

        verses: list[str] = []
        for i in range(int(start), int(end) + 1):
            url = f'{self.BASE_URL}/verses/{version}/{abbrev}/{chapter}/{i}'
            resp = await HttpClient.get(url, headers=headers)
            resp.raise_for_status()
            verses.append(f'> {resp.json()["text"]}')

        text = f'*{book} {chapter}:{start}-{end}*\n\n' + '\n'.join(verses)
        return [Reply.to(data).text(text)]

    async def _resolve_abbrev(self, data: CommandData, book: str) -> str | list[BotMessage]:
        headers = self._auth_headers()
        books_resp = await HttpClient.get(f'{self.BASE_URL}/books', headers=headers)
        books_resp.raise_for_status()
        books = books_resp.json()

        abbrev = self._find_abbrev(books, book)
        if not abbrev:
            return [self._books_not_found(data, books)]
        return abbrev

    @staticmethod
    def _find_abbrev(books: list[dict], book_name: str) -> str | None:
        for b in books:
            if b['name'].lower() == book_name.lower():
                return b.get('abbrev', {}).get('pt')
        return None

    @staticmethod
    def _build_verse(data: CommandData, verse: dict) -> BotMessage:
        book_name = verse['book']['name']
        chapter = verse['chapter']
        number = verse['number']
        text = verse['text']
        return Reply.to(data).text(f'*{book_name} {chapter}:{number}*\n\n> {text}')

    @staticmethod
    def _books_not_found(data: CommandData, books: list[dict]) -> BotMessage:
        book_names = '\n'.join(f'- {b["name"]}' for b in books)
        text = 'Não consegui encontrar o livro que você digitou... 😔'
        text += '\n\n📚 *Livros Disponíveis* 📚\n'
        text += book_names
        return Reply.to(data).text(text)
