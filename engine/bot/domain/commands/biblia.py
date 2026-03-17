import os
import re

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, OptionDef, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient


class BibliaCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='bíblia',
            options=[
                OptionDef(name='lang', values=['pt', 'en']),
                OptionDef(name='version', values=['nvi', 'ra', 'acf', 'kjv', 'bbe', 'apee', 'rvr']),
            ],
            args=ArgType.OPTIONAL,
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Comando complexo. Use *,menu biblia* para detalhes.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        rest = parsed.rest.strip()
        has_verse = re.search(r'\d{1,3}\s*:\s*\d{1,3}\s*(?:-\s*\d{1,3})?', rest)
        version = parsed.options.get('version', 'nvi')
        token = os.environ.get('BIBLIA_TOKEN', '')
        headers = {'Authorization': f'Bearer {token}'}
        base_url = 'https://www.abibliadigital.com.br/api'

        if not has_verse:
            url = f'{base_url}/verses/{version}/random'
            response = await HttpClient.get(url, headers=headers)
            response.raise_for_status()
            return [self._build_verse(data, response.json())]

        book = re.sub(r'\d{1,3}\s*:\s*\d{1,3}\s*(?:-\s*\d{1,3})?', '', rest).strip()
        if not book:
            return [Reply.to(data).text('Por favor, digite o nome do livro da bíblia... 😔')]

        chapter_match = re.search(r'(\d{1,3}):', rest)
        chapter = chapter_match.group(1) if chapter_match else ''

        has_range = re.search(r'-\s*\d{1,3}', rest)

        if not has_range:
            number_match = re.search(r':\s*(\d{1,3})', rest)
            number = number_match.group(1) if number_match else ''

            books_resp = await HttpClient.get(f'{base_url}/books', headers=headers)
            books_resp.raise_for_status()
            books = books_resp.json()

            abbrev = self._find_abbrev(books, book)
            if not abbrev:
                return [self._books_not_found(data, books)]

            url = f'{base_url}/verses/{version}/{abbrev}/{chapter}/{number}'
            response = await HttpClient.get(url, headers=headers)
            response.raise_for_status()
            return [self._build_verse(data, response.json())]

        range_match = re.search(r'(\d{1,3})\s*-\s*(\d{1,3})', rest)
        start = range_match.group(1) if range_match else '1'
        end = range_match.group(2) if range_match else '1'

        books_resp = await HttpClient.get(f'{base_url}/books', headers=headers)
        books_resp.raise_for_status()
        books = books_resp.json()

        abbrev = self._find_abbrev(books, book)
        if not abbrev:
            return [self._books_not_found(data, books)]

        verses: list[str] = []
        for i in range(int(start), int(end) + 1):
            url = f'{base_url}/verses/{version}/{abbrev}/{chapter}/{i}'
            resp = await HttpClient.get(url, headers=headers)
            resp.raise_for_status()
            verses.append(f'> {resp.json()["text"]}')

        text = f'*{book} {chapter}:{start}-{end}*\n\n' + '\n'.join(verses)
        return [Reply.to(data).text(text)]

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
