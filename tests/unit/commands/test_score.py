from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest

from bot.domain.commands.score import (
    ScoreCommand,
    _apply_soft_cap,
    _format_date_label,
    _score_emoji,
)
from bot.domain.models.football import MatchStatus, TmLiveMatch
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return ScoreCommand()


def _make_match(  # noqa: PLR0913
    home_team: str,
    away_team: str,
    home_score: int | None,
    away_score: int | None,
    competition_name: str = 'Brasileirão',
    competition_code: str = 'BRA1',
    country: str = 'Brasil',
    country_flag_emoji: str = '🇧🇷',
    match_time: str = "45'",
    status: MatchStatus = MatchStatus.LIVE,
    match_id: str = '12345',
) -> TmLiveMatch:
    return TmLiveMatch(
        competition_code=competition_code,
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


class TestFormatDateLabel:
    @pytest.mark.parametrize(
        ('match_time', 'expected'),
        [
            ('14:00', 'Hoje'),
            ('23:59', 'Hoje'),
        ],
    )
    def test_returns_hoje_for_today(self, match_time, expected, mocker):
        from datetime import datetime as datetime_cls

        mocker.patch(
            'bot.domain.services.score_formatter._get_current_datetime',
            return_value=datetime_cls(2025, 6, 15, 12, 0),  # noqa: DTZ001
        )
        mocker.patch(
            'bot.domain.services.score_formatter._get_current_date',
            return_value=date(2025, 6, 15),
        )
        assert _format_date_label(match_time) == expected

    @pytest.mark.parametrize(
        ('match_time', 'expected'),
        [
            ('10:00', 'Amanhã'),
            ('20:00', 'Amanhã'),
        ],
    )
    def test_returns_amanha_for_tomorrow(self, match_time, expected, mocker):
        from datetime import datetime as datetime_cls

        mocker.patch(
            'bot.domain.services.score_formatter._get_current_datetime',
            return_value=datetime_cls(2025, 6, 15, 12, 0),  # noqa: DTZ001
        )
        mocker.patch(
            'bot.domain.services.score_formatter._get_current_date',
            return_value=date(2025, 6, 14),
        )
        assert _format_date_label(match_time) == expected

    def test_returns_date_format_for_future(self, mocker):
        from datetime import datetime as datetime_cls

        mocker.patch(
            'bot.domain.services.score_formatter._get_current_datetime',
            return_value=datetime_cls(2025, 6, 15, 12, 0),  # noqa: DTZ001
        )
        mocker.patch(
            'bot.domain.services.score_formatter._get_current_date',
            return_value=date(2025, 6, 15),
        )
        assert _format_date_label('14:00') == 'Hoje'

    def test_returns_empty_for_invalid_time(self):
        assert _format_date_label('') == ''
        assert _format_date_label('invalid') == ''


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
            'bot.domain.commands.score.TransfermarktService.fetch_live_matches',
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
                competition_code='GB1',
                country='Inglaterra',
                country_flag_emoji='🏴󠁧󠁢󠁥󠁮󠁧󠁿',
            ),
        ]

        with patch(
            'bot.domain.commands.score.TransfermarktService.fetch_live_matches',
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
            'bot.domain.commands.score.TransfermarktService.fetch_live_matches',
            new_callable=AsyncMock,
            return_value=matches,
        ):
            messages = await command.run(data)

        content = messages[0].content
        assert isinstance(content, TextContent)
        assert '2️⃣ x 1️⃣' in content.text
        assert "67'" in content.text

    @pytest.mark.anyio
    async def test_formats_not_started_match_with_time(self, command, mocker):
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

        mocker.patch(
            'bot.domain.services.score_formatter._get_current_datetime',
            return_value=datetime(2025, 6, 15, 12, 0),  # noqa: DTZ001
        )
        mocker.patch(
            'bot.domain.services.score_formatter._get_current_date',
            return_value=date(2025, 6, 15),
        )

        with patch(
            'bot.domain.commands.score.TransfermarktService.fetch_live_matches',
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
            'bot.domain.commands.score.TransfermarktService.fetch_live_matches',
            new_callable=AsyncMock,
            return_value=matches,
        ):
            messages = await command.run(data)

        content = messages[0].content
        assert isinstance(content, TextContent)
        assert '🔟' in content.text
        assert '0️⃣' in content.text

    @pytest.mark.anyio
    async def test_separates_live_and_upcoming_matches(self, command, mocker):
        data = GroupCommandDataFactory.build(text='/placar')
        matches = [
            _make_match('Flamengo', 'Palmeiras', 2, 1, match_time="67'", status=MatchStatus.LIVE),
            _make_match(
                'Botafogo',
                'Fluminense',
                None,
                None,
                match_time='16:00',
                status=MatchStatus.NOT_STARTED,
            ),
        ]

        mocker.patch(
            'bot.domain.services.score_formatter._get_current_datetime',
            return_value=datetime(2025, 6, 15, 12, 0),  # noqa: DTZ001
        )
        mocker.patch(
            'bot.domain.services.score_formatter._get_current_date',
            return_value=date(2025, 6, 15),
        )

        with patch(
            'bot.domain.commands.score.TransfermarktService.fetch_live_matches',
            new_callable=AsyncMock,
            return_value=matches,
        ):
            messages = await command.run(data)

        content = messages[0].content
        assert isinstance(content, TextContent)
        text = content.text
        assert '🔥 *Ao Vivo*' in text
        assert '📅 *Próximos Jogos*' in text

    @pytest.mark.anyio
    async def test_upcoming_matches_show_date_label(self, command, mocker):
        data = GroupCommandDataFactory.build(text='/placar')
        matches = [
            _make_match(
                'Botafogo',
                'Fluminense',
                None,
                None,
                match_time='14:00',
                status=MatchStatus.NOT_STARTED,
            ),
        ]

        mocker.patch(
            'bot.domain.services.score_formatter._get_current_datetime',
            return_value=datetime(2025, 6, 15, 12, 0),  # noqa: DTZ001
        )
        mocker.patch(
            'bot.domain.services.score_formatter._get_current_date',
            return_value=date(2025, 6, 15),
        )

        with patch(
            'bot.domain.commands.score.TransfermarktService.fetch_live_matches',
            new_callable=AsyncMock,
            return_value=matches,
        ):
            messages = await command.run(data)

        content = messages[0].content
        assert isinstance(content, TextContent)
        assert 'Hoje 🕐 14:00' in content.text

    @pytest.mark.anyio
    async def test_upcoming_only_no_live_section(self, command, mocker):
        data = GroupCommandDataFactory.build(text='/placar')
        matches = [
            _make_match(
                'Botafogo',
                'Fluminense',
                None,
                None,
                match_time='18:00',
                status=MatchStatus.NOT_STARTED,
            ),
        ]

        mocker.patch(
            'bot.domain.services.score_formatter._get_current_datetime',
            return_value=datetime(2025, 6, 15, 12, 0),  # noqa: DTZ001
        )
        mocker.patch(
            'bot.domain.services.score_formatter._get_current_date',
            return_value=date(2025, 6, 15),
        )

        with patch(
            'bot.domain.commands.score.TransfermarktService.fetch_live_matches',
            new_callable=AsyncMock,
            return_value=matches,
        ):
            messages = await command.run(data)

        content = messages[0].content
        assert isinstance(content, TextContent)
        text = content.text
        assert '🔥 *Ao Vivo*' not in text
        assert '📅 *Próximos Jogos*' in text


def _finished(
    competition_code: str,
    competition_name: str,
    home_team: str,
    away_team: str,
    match_id: str,
) -> TmLiveMatch:
    return _make_match(
        home_team=home_team,
        away_team=away_team,
        home_score=1,
        away_score=0,
        competition_code=competition_code,
        competition_name=competition_name,
        status=MatchStatus.FINISHED,
        match_id=match_id,
    )


class TestApplySoftCap:
    def test_brasileirao_always_included_even_when_alphabetically_last(self):
        matches = [
            _finished('RU1', 'Premier Liga', 'Zenit', 'Spartak', '1'),
            _finished('SA1', 'Saudi Pro League', 'Al-Hilal', 'Al-Nassr', '2'),
            _finished('A1', 'Austrian Bundesliga', 'Salzburg', 'Rapid', '3'),
            _finished('BRA1', 'Brasileirão', 'Flamengo', 'Palmeiras', '4'),
        ]

        picked = _apply_soft_cap(matches, soft_cap=7)

        codes = [m.competition_code for m in picked]
        assert codes[0] == 'BRA1'
        assert 'BRA1' in codes

    def test_whole_league_kept_even_when_overflow(self):
        top5 = [_finished('GB1', 'Premier League', f'H{i}', f'A{i}', f'g{i}') for i in range(6)]
        ar = [_finished('AR1N', 'Liga Profesional', f'AH{i}', f'AA{i}', f'a{i}') for i in range(3)]

        picked = _apply_soft_cap([*top5, *ar], soft_cap=7)

        assert len(picked) == 9
        assert sum(1 for m in picked if m.competition_code == 'GB1') == 6
        assert sum(1 for m in picked if m.competition_code == 'AR1N') == 3

    def test_stops_after_soft_cap_reached(self):
        top5 = [_finished('GB1', 'Premier League', f'H{i}', f'A{i}', f'g{i}') for i in range(8)]
        low = [_finished('ZZZ', 'Long Tail', 'X', 'Y', 'z')]

        picked = _apply_soft_cap([*top5, *low], soft_cap=7)

        assert len(picked) == 8
        assert all(m.competition_code == 'GB1' for m in picked)

    def test_priority_ordering_brasileirao_before_europe_before_rest(self):
        matches = [
            _finished('MEX1', 'Liga MX', 'A', 'B', '1'),
            _finished('GB1', 'Premier League', 'C', 'D', '2'),
            _finished('BRA1', 'Brasileirão', 'E', 'F', '3'),
        ]

        picked = _apply_soft_cap(matches, soft_cap=7)

        assert [m.competition_code for m in picked] == ['BRA1', 'GB1', 'MEX1']


class TestFlagOverridesAreDeduplicated:
    def test_overrides_resolve_from_nationality_flag(self):
        from bot.data.nationality_flags import nationality_flag
        from bot.data.transfermarkt_country_codes import COMPETITION_CODE_OVERRIDES

        assert COMPETITION_CODE_OVERRIDES['BRNE'] == nationality_flag('Brasil')
        assert COMPETITION_CODE_OVERRIDES['CNAT'] == nationality_flag('Inglaterra')
        assert COMPETITION_CODE_OVERRIDES['KR1'] == nationality_flag('Croácia')
        assert COMPETITION_CODE_OVERRIDES['RLB3'] == nationality_flag('Alemanha')
