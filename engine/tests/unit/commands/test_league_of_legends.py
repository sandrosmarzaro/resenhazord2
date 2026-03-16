from unittest.mock import MagicMock, patch

import pytest

from bot.domain.commands.league_of_legends import LeagueOfLegendsCommand
from bot.domain.models.message import ImageContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return LeagueOfLegendsCommand()


def _mock_versions_response():
    mock = MagicMock()
    mock.json.return_value = ['14.1.1', '14.1.0']
    mock.raise_for_status.return_value = None
    return mock


def _mock_champions_response():
    mock = MagicMock()
    mock.json.return_value = {
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
    mock.raise_for_status.return_value = None
    return mock


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
    async def test_calls_version_and_champions_apis(self, command):
        data = GroupCommandDataFactory.build(text=', lol')
        version_resp = _mock_versions_response()
        champs_resp = _mock_champions_response()

        with patch(
            'bot.domain.commands.league_of_legends.HttpClient.get',
            side_effect=[version_resp, champs_resp],
        ) as mock_get:
            await command.run(data)

            assert mock_get.call_count == 2

    @pytest.mark.anyio
    async def test_returns_image_with_champion_info(self, command):
        data = GroupCommandDataFactory.build(text=', lol')
        version_resp = _mock_versions_response()
        champs_resp = _mock_champions_response()

        with patch(
            'bot.domain.commands.league_of_legends.HttpClient.get',
            side_effect=[version_resp, champs_resp],
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert 'Ahri_0.jpg' in messages[0].content.url
        caption = messages[0].content.caption
        assert 'Ahri' in caption
        assert 'Nine-Tailed Fox' in caption
        assert 'Mage' in caption
        assert 'Ataque: 3/10' in caption

    @pytest.mark.anyio
    async def test_returns_error_on_failure(self, command):
        data = GroupCommandDataFactory.build(text=', lol')

        with patch(
            'bot.domain.commands.league_of_legends.HttpClient.get',
            side_effect=Exception('API down'),
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text
