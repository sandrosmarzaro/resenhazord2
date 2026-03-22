import httpx
import pytest

from bot.domain.commands.league_of_legends import LeagueOfLegendsCommand
from bot.domain.models.message import ImageContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory

VERSIONS_URL = 'https://ddragon.leagueoflegends.com/api/versions.json'

MOCK_CHAMPIONS = {
    'data': {
        'Ahri': {
            'id': 'Ahri',
            'name': 'Ahri',
            'title': 'the Nine-Tailed Fox',
            'tags': ['Mage', 'Assassin'],
            'info': {'attack': 3, 'defense': 4, 'magic': 8, 'difficulty': 5},
            'blurb': 'A vastayan with fox-like features.',
        }
    }
}


@pytest.fixture
def command():
    return LeagueOfLegendsCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', lol', True),
            (',lol', True),
            (', LOL', True),
            (', lol show', True),
            (', lol dm', True),
            ('  , lol  ', True),
            ('lol', False),
            ('hello', False),
            (', lol extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_calls_version_and_champions_apis(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', lol')
        versions_route = respx_mock.get(VERSIONS_URL).mock(
            return_value=httpx.Response(200, json=['14.1.1', '14.1.0'])
        )
        champs_route = respx_mock.get(
            url__startswith='https://ddragon.leagueoflegends.com/cdn/'
        ).mock(return_value=httpx.Response(200, json=MOCK_CHAMPIONS))
        await command.run(data)

        assert versions_route.call_count == 1
        assert champs_route.call_count == 1

    @pytest.mark.anyio
    async def test_returns_image_with_champion_info(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', lol')
        respx_mock.get(VERSIONS_URL).mock(
            return_value=httpx.Response(200, json=['14.1.1', '14.1.0'])
        )
        respx_mock.get(url__startswith='https://ddragon.leagueoflegends.com/cdn/').mock(
            return_value=httpx.Response(200, json=MOCK_CHAMPIONS)
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert 'Ahri_0.jpg' in messages[0].content.url
        caption = messages[0].content.caption
        assert caption is not None
        assert 'Ahri' in caption
        assert 'Nine-Tailed Fox' in caption
        assert 'Mage' in caption
        assert '3/10' in caption

    @pytest.mark.anyio
    async def test_returns_error_on_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', lol')
        respx_mock.get(VERSIONS_URL).mock(side_effect=Exception('API down'))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text
