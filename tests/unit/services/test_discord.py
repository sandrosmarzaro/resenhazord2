import pytest

from bot.domain.services.discord import DiscordService


class TestNormalize:
    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('Churrasco', 'churrasco'),
            ('Dev Ops', 'dev-ops'),
            ('café', 'cafe'),
            ('São Paulo', 'sao-paulo'),
            ('Múltiplos  Espaços', 'multiplos-espacos'),
        ],
    )
    def test_normalize(self, name, expected):
        assert DiscordService._normalize(name) == expected


class TestNameMatches:
    @pytest.mark.parametrize(
        ('channel_name', 'search_name', 'expected'),
        [
            ('churrasco', 'churrasco', True),
            ('Churrasco', 'churrasco', True),
            ('churrasco', 'CHURRASCO', True),
            ('cafe', 'café', True),
            ('sao-paulo', 'São Paulo', True),
            ('churrasco', 'festa', False),
        ],
    )
    def test_name_matches(self, channel_name, search_name, expected):
        assert DiscordService._name_matches(channel_name, search_name) is expected


class TestFindCategory:
    TOKEN = 't'  # noqa: S105

    def test_finds_matching_category(self):
        svc = DiscordService(token=self.TOKEN, guild_id='g')
        channels = [
            {'id': '1', 'name': '2026', 'type': 4},
            {'id': '2', 'name': 'geral', 'type': 0},
        ]

        result = svc.find_category(channels, '2026')

        assert result is not None
        assert result['id'] == '1'

    def test_returns_none_when_not_found(self):
        svc = DiscordService(token=self.TOKEN, guild_id='g')
        channels = [{'id': '1', 'name': '2026', 'type': 4}]

        assert svc.find_category(channels, '2025') is None


class TestFindChannel:
    TOKEN = 't'  # noqa: S105

    def test_finds_matching_channel(self):
        svc = DiscordService(token=self.TOKEN, guild_id='g')
        channels = [
            {'id': 'ch-1', 'name': 'churrasco', 'type': 0, 'parent_id': 'cat-1'},
            {'id': 'ch-2', 'name': 'churrasco', 'type': 0, 'parent_id': 'cat-2'},
        ]

        result = svc.find_channel(channels, 'churrasco', 'cat-1')

        assert result is not None
        assert result['id'] == 'ch-1'

    def test_returns_none_for_wrong_parent(self):
        svc = DiscordService(token=self.TOKEN, guild_id='g')
        channels = [
            {'id': 'ch-1', 'name': 'churrasco', 'type': 0, 'parent_id': 'cat-1'},
        ]

        assert svc.find_channel(channels, 'churrasco', 'cat-99') is None
