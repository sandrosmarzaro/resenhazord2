import httpx
import pytest

from bot.domain.commands.bible import BibleCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory

RANDOM_URL = 'https://bible-api.com/data/almeida/random'


@pytest.fixture
def command():
    return BibleCommand()


def _random_response():
    return {
        'random_verse': {
            'book': 'Gênesis',
            'chapter': 1,
            'verse': 1,
            'text': 'No princípio criou Deus os céus e a terra.   ',
        }
    }


def _passage_response(reference, *texts):
    return {
        'reference': reference,
        'verses': [{'text': f'{text}   '} for text in texts],
    }


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
        respx_mock.get(RANDOM_URL).mock(return_value=httpx.Response(200, json=_random_response()))

        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert messages[0].content.text == (
            '*Gênesis 1:1*\n\n> No princípio criou Deus os céus e a terra.'
        )


class TestPassage:
    @pytest.mark.anyio
    async def test_specific_verse(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia joão 3:16')
        route = respx_mock.get('https://bible-api.com/joão 3:16').mock(
            return_value=httpx.Response(200, json=_passage_response('João 3:16', 'Porque Deus'))
        )

        messages = await command.run(data)

        assert route.calls.last.request.url.params['translation'] == 'almeida'
        assert messages[0].content.text == '*João 3:16*\n\n> Porque Deus'

    @pytest.mark.anyio
    async def test_verse_range(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia Gênesis 1:1-3')
        respx_mock.get('https://bible-api.com/Gênesis 1:1-3').mock(
            return_value=httpx.Response(
                200, json=_passage_response('Gênesis 1:1-3', 'Verso 1', 'Verso 2', 'Verso 3')
            )
        )

        messages = await command.run(data)

        assert messages[0].content.text == ('*Gênesis 1:1-3*\n\n> Verso 1\n> Verso 2\n> Verso 3')

    @pytest.mark.anyio
    async def test_reference_not_found(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia Xablau 1:1')
        respx_mock.get('https://bible-api.com/Xablau 1:1').mock(
            return_value=httpx.Response(404, json={'error': 'not found'})
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
        respx_mock.get(RANDOM_URL).mock(return_value=httpx.Response(500))

        messages = await command.run(data)

        assert 'fora do ar' in messages[0].content.text
