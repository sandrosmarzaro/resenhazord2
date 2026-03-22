import httpx
import pytest

from bot.domain.commands.bible import BibleCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return BibleCommand(biblia_token='test-token')  # noqa: S106


def _verse_response(**overrides):
    return {
        'book': {'name': 'Gênesis'},
        'chapter': 1,
        'number': 1,
        'text': 'No princípio, Deus criou os céus e a terra.',
        **overrides,
    }


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', bíblia', True),
            (',bíblia', True),
            (', biblia', True),
            (', BÍBLIA', True),
            (', bíblia nvi', True),
            (', bíblia kjv', True),
            (', bíblia Gênesis 1:1', True),
            ('  , bíblia  ', True),
            ('bíblia', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_random_verse_when_no_args(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia')
        route = respx_mock.get(url__regex=r'.*/verses/.*/random').mock(
            return_value=httpx.Response(200, json=_verse_response())
        )
        messages = await command.run(data)

        url = str(route.calls.last.request.url)
        assert '/random' in url
        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Gênesis 1:1' in messages[0].content.text

    @pytest.mark.anyio
    async def test_uses_specified_version(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia kjv')
        route = respx_mock.get(url__regex=r'.*/verses/.*/random').mock(
            return_value=httpx.Response(200, json=_verse_response())
        )
        await command.run(data)

        url = str(route.calls.last.request.url)
        assert '/kjv/' in url

    @pytest.mark.anyio
    async def test_specific_verse(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia Gênesis 1:1')
        books_route = respx_mock.get(url__regex=r'.*/books$').mock(
            return_value=httpx.Response(200, json=[{'name': 'Gênesis', 'abbrev': {'pt': 'gn'}}])
        )
        verse_route = respx_mock.get(url__regex=r'.*/verses/.*/gn/\d+/\d+').mock(
            return_value=httpx.Response(200, json=_verse_response())
        )
        messages = await command.run(data)

        assert books_route.called
        verse_url = str(verse_route.calls.last.request.url)
        assert '/gn/' in verse_url
        assert 'Gênesis 1:1' in messages[0].content.text

    @pytest.mark.anyio
    async def test_book_not_found(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia Xablau 1:1')
        respx_mock.get(url__regex=r'.*/books$').mock(
            return_value=httpx.Response(200, json=[{'name': 'Gênesis', 'abbrev': {'pt': 'gn'}}])
        )
        messages = await command.run(data)

        assert 'Não consegui encontrar' in messages[0].content.text

    @pytest.mark.anyio
    async def test_missing_book_name_returns_error(self, command):
        data = GroupCommandDataFactory.build(text=', bíblia 1:1')

        messages = await command.run(data)

        assert 'Por favor, digite o nome' in messages[0].content.text

    @pytest.mark.anyio
    async def test_verse_range(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bíblia Gênesis 1:1-3')
        respx_mock.get(url__regex=r'.*/books$').mock(
            return_value=httpx.Response(200, json=[{'name': 'Gênesis', 'abbrev': {'pt': 'gn'}}])
        )
        respx_mock.get(url__regex=r'.*/verses/.*/gn/\d+/\d+').mock(
            side_effect=[
                httpx.Response(200, json={'text': 'Verso 1'}),
                httpx.Response(200, json={'text': 'Verso 2'}),
                httpx.Response(200, json={'text': 'Verso 3'}),
            ]
        )
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Gênesis 1:1-3' in text
        assert 'Verso 1' in text
        assert 'Verso 3' in text
