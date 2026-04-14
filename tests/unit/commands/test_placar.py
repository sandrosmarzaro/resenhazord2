from unittest.mock import AsyncMock, patch

import pytest

from bot.domain.commands.placar import PlacarCommand, _score_emoji
from bot.domain.models.football import MatchStatus, TmLiveMatch
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return PlacarCommand()


def _make_match(
    home_team: str,
    away_team: str,
    home_score: int | None,
    away_score: int | None,
    competition_name: str = 'Brasileirão',
    country: str = 'Brasil',
    country_flag_emoji: str = '🇧🇷',
    match_time: str = "45'",
    status: MatchStatus = MatchStatus.LIVE,
    match_id: str = '12345',
) -> TmLiveMatch:
    return TmLiveMatch(
        competition_code='BR1',
        competition_name=competition_name,
        country=country,
        country_flag_emoji=country_flag_emoji,
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        match_time=match_time,
        status=status,
        match_id=match_id,
    )


class TestScoreEmoji:
    def test_none_returns_dash(self):
        assert _score_emoji(None) == '-'

    def test_zero_returns_zero_emoji(self):
        assert _score_emoji(0) == '0️⃣'

    def test_number_returns_emoji(self):
        assert _score_emoji(1) == '1️⃣'
        assert _score_emoji(5) == '5️⃣'

    def test_ten_returns_keycap_ten(self):
        assert _score_emoji(10) == '🔟'

    def test_above_ten_returns_string(self):
        assert _score_emoji(11) == '11'
        assert _score_emoji(99) == '99'


class TestConfig:
    def test_name(self, command):
        assert command.config.name == 'placar'

    def test_alias(self, command):
        assert 'score' in command.config.aliases

    def test_category(self, command):
        from bot.domain.commands.base import Category

        assert command.config.category == Category.OTHER

    def test_platforms(self, command):
        from bot.domain.commands.base import Platform

        assert Platform.WHATSAPP in command.config.platforms
        assert Platform.DISCORD in command.config.platforms


class TestMenuDescription:
    def test_description(self, command):
        assert command.menu_description == 'Jogos de futebol ao vivo.'


class TestExecute:
    @pytest.mark.anyio
    async def test_empty_matches_returns_no_live_message(self, command):
        data = GroupCommandDataFactory.build(text='/placar')

        with patch(
            'bot.domain.commands.placar.TransfermarktService.fetch_live_matches',
            new_callable=AsyncMock,
            return_value=[],
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        content = messages[0].content
        assert isinstance(content, TextContent)
        assert 'Nenhum jogo ao vivo agora' in content.text

    @pytest.mark.anyio
    async def test_groups_matches_by_competition(self, command):
        data = GroupCommandDataFactory.build(text='/placar')
        matches = [
            _make_match('Flamengo', 'Palmeiras', 2, 1),
            _make_match('Corinthians', 'Santos', 0, 0),
            _make_match(
                'Arsenal',
                'Liverpool',
                1,
                1,
                competition_name='Premier League',
                country='Inglaterra',
                country_flag_emoji='🏴󠁧󠁢󠁥󠁮󠁧󠁿',
            ),
        ]

        with patch(
            'bot.domain.commands.placar.TransfermarktService.fetch_live_matches',
            new_callable=AsyncMock,
            return_value=matches,
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        content = messages[0].content
        assert isinstance(content, TextContent)
        text = content.text
        assert '🇧🇷 *Brasileirão*' in text
        assert '🏴󠁧󠁢󠁥󠁮󠁧󠁿 *Premier League*' in text

    @pytest.mark.anyio
    async def test_formats_match_with_scores_and_time(self, command):
        data = GroupCommandDataFactory.build(text='/placar')
        matches = [
            _make_match('Flamengo', 'Palmeiras', 2, 1, match_time="67'"),
        ]

        with patch(
            'bot.domain.commands.placar.TransfermarktService.fetch_live_matches',
            new_callable=AsyncMock,
            return_value=matches,
        ):
            messages = await command.run(data)

        content = messages[0].content
        assert isinstance(content, TextContent)
        assert '2️⃣ x 1️⃣' in content.text
        assert "67'" in content.text

    @pytest.mark.anyio
    async def test_formats_not_started_match_with_time(self, command):
        data = GroupCommandDataFactory.build(text='/placar')
        matches = [
            _make_match(
                'Botafogo',
                'Fluminense',
                None,
                None,
                match_time='16:00',
                status=MatchStatus.NOT_STARTED,
            ),
        ]

        with patch(
            'bot.domain.commands.placar.TransfermarktService.fetch_live_matches',
            new_callable=AsyncMock,
            return_value=matches,
        ):
            messages = await command.run(data)

        content = messages[0].content
        assert isinstance(content, TextContent)
        assert '- x -' in content.text
        assert '16:00' in content.text

    @pytest.mark.anyio
    async def test_uses_number_emoji_for_scores(self, command):
        data = GroupCommandDataFactory.build(text='/placar')
        matches = [
            _make_match('Time A', 'Time B', 10, 0),
        ]

        with patch(
            'bot.domain.commands.placar.TransfermarktService.fetch_live_matches',
            new_callable=AsyncMock,
            return_value=matches,
        ):
            messages = await command.run(data)

        content = messages[0].content
        assert isinstance(content, TextContent)
        assert '🔟' in content.text
        assert '0️⃣' in content.text
