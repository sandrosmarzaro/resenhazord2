import re

import httpx
import pytest
from structlog.testing import capture_logs

from bot.data.bible import BIBLE_CHAPTERS
from bot.domain.commands.bible import BibleCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory

CHAPTER_URL = re.compile(r'https://api\.getbible\.net/v2/livre/(\d+)/(\d+)\.json')
QUERY_URL = 'https://query.getbible.net/v2/livre'


@pytest.fixture
def command():
    return BibleCommand()


def _verse(book, chapter, verse, text):
    return {'chapter': chapter, 'verse': verse, 'name': f'{book} {chapter}:{verse}', 'text': text}


def _chapter(book, chapter, ref, *verses):
    return {
        'book_name': book,
        'chapter': chapter,
        'ref': [ref],
        'verses': [_verse(book, chapter, verse, f'{text} ') for verse, text in verses],
    }


def _problem(code):
    return {'status': 404, 'code': code, 'detail': 'Not Found'}


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', bíblia', True),
            (',bíblia', True),
            (', biblia', True),
            (', BÍBLIA', True),
            (', bíblia Gênesis 1:1', True),
            ('  , bíblia  ', True),
            ('bíblia', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRandom:
    @pytest.mark.anyio
    async def test_random_verse_when_no_args(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia')
        chapter = _chapter(
            'Gênesis', 1, 'Gênesis 1', (1, 'No princípio criou Deus os céus e a terra.')
        )
        respx_mock.get(CHAPTER_URL).mock(return_value=httpx.Response(200, json=chapter))

        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert messages[0].content.text == (
            '*Gênesis 1:1*\n\n> No princípio criou Deus os céus e a terra.'
        )

    @pytest.mark.anyio
    async def test_draws_a_chapter_that_exists(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia')
        chapter = _chapter('Gênesis', 1, 'Gênesis 1', (1, 'Verso'))
        route = respx_mock.get(CHAPTER_URL).mock(return_value=httpx.Response(200, json=chapter))

        await command.run(data)

        book, chapter_number = CHAPTER_URL.match(str(route.calls.last.request.url)).groups()
        assert 1 <= int(chapter_number) <= BIBLE_CHAPTERS[int(book)]


class TestPassage:
    @pytest.mark.anyio
    async def test_specific_verse(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia joão 3:16')
        respx_mock.get(f'{QUERY_URL}/joão 3:16').mock(
            return_value=httpx.Response(
                200, json={'livre_43_3': _chapter('João', 3, 'joão 3:16', (16, 'Porque Deus'))}
            )
        )

        messages = await command.run(data)

        assert messages[0].content.text == '*João 3:16*\n\n> Porque Deus'

    @pytest.mark.anyio
    async def test_verse_range(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia Gênesis 1:1-3')
        chapter = _chapter(
            'Gênesis', 1, 'Gênesis 1:1-3', (1, 'Verso 1'), (2, 'Verso 2'), (3, 'Verso 3')
        )
        respx_mock.get(f'{QUERY_URL}/Gênesis 1:1-3').mock(
            return_value=httpx.Response(200, json={'livre_1_1': chapter})
        )

        messages = await command.run(data)

        assert messages[0].content.text == '*Gênesis 1:1-3*\n\n> Verso 1\n> Verso 2\n> Verso 3'

    @pytest.mark.anyio
    async def test_spaces_around_separators_are_dropped(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia joão 3 : 16 - 17')
        route = respx_mock.get(f'{QUERY_URL}/joão 3:16-17').mock(
            return_value=httpx.Response(
                200, json={'livre_43_3': _chapter('João', 3, 'joão 3:16-17', (16, 'A'), (17, 'B'))}
            )
        )

        await command.run(data)

        assert route.called

    @pytest.mark.anyio
    async def test_references_across_chapters(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia joão 3:16;4:1')
        respx_mock.get(f'{QUERY_URL}/joão 3:16;4:1').mock(
            return_value=httpx.Response(
                200,
                json={
                    'livre_43_3': _chapter('João', 3, 'João 3:16', (16, 'A')),
                    'livre_43_4': _chapter('João', 4, '4:1', (1, 'B')),
                },
            )
        )

        messages = await command.run(data)

        assert messages[0].content.text == '*João 3:16*\n\n> A\n\n*João 4:1*\n\n> B'

    @pytest.mark.anyio
    @pytest.mark.parametrize('code', ['invalid_reference', 'not_found'])
    async def test_reference_not_found(self, command, respx_mock, code):
        data = GroupCommandDataFactory.build(text=', bíblia Xablau 1:1')
        respx_mock.get(f'{QUERY_URL}/Xablau 1:1').mock(
            return_value=httpx.Response(404, json=_problem(code))
        )

        messages = await command.run(data)

        assert 'Não consegui encontrar' in messages[0].content.text

    @pytest.mark.anyio
    async def test_reference_without_verse_asks_for_format(self, command):
        data = GroupCommandDataFactory.build(text=', bíblia joão')

        messages = await command.run(data)

        assert 'livro capítulo:versículo' in messages[0].content.text


class TestErrors:
    @pytest.mark.anyio
    async def test_api_down_returns_friendly_message(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia')
        respx_mock.get(CHAPTER_URL).mock(return_value=httpx.Response(500))

        messages = await command.run(data)

        assert 'fora do ar' in messages[0].content.text

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'response',
        [
            httpx.Response(404, json=_problem('translation_not_found')),
            httpx.Response(404, text='<html>404 Not Found</html>'),
        ],
        ids=['translation removed', 'not json'],
    )
    async def test_upstream_404_is_logged_as_failure(self, command, respx_mock, response):
        data = GroupCommandDataFactory.build(text=', bíblia joão 3:16')
        respx_mock.get(f'{QUERY_URL}/joão 3:16').mock(return_value=response)

        with capture_logs() as logs:
            messages = await command.run(data)

        assert 'fora do ar' in messages[0].content.text
        assert [log['upstream'] for log in logs if log['event'] == 'upstream_failed'] == [
            'getbible'
        ]
