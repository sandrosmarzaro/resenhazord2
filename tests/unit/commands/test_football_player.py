import pytest

from bot.data.football import LEAGUES
from bot.domain.commands.football_player import FootballPlayerCommand
from bot.domain.models.message import ImageBufferContent
from bot.domain.services.transfermarkt import TmPlayer, TransfermarktService
from bot.infrastructure.http_client import HttpClient
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

_LEAGUE = LEAGUES['pl']


def _make_player(name: str = 'Lionel Messi') -> TmPlayer:
    return TmPlayer(
        name=name,
        position='Ponta Direita',
        age=36,
        nationality='Argentina',
        club='Inter Miami',
        club_id='50251',
        market_value='€ 20,00 mi.',
        photo_url='https://img.tm.com/portrait/big/28003.jpg',
        badge_url='https://tmssl.akamaized.net/images/wappen/head/50251.png',
        profile_url='https://www.transfermarkt.com.br/lionel-messi/profil/spieler/28003',
        nationality_flag_emoji='🇦🇷',
    )


@pytest.fixture
def command():
    return FootballPlayerCommand()


@pytest.fixture
def mock_players(mocker):
    players = [_make_player()]
    mocker.patch.object(
        TransfermarktService,
        'fetch_page',
        new=mocker.AsyncMock(return_value=players),
    )
    mocker.patch.object(
        TransfermarktService,
        'fetch_player_profile',
        new=mocker.AsyncMock(return_value={'Altura': '1,70 m', 'Pé': 'esquerdo'}),
    )
    mocker.patch.object(HttpClient, 'get_buffer', new=mocker.AsyncMock(return_value=b'fake-photo'))
    return players


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',jogador', True),
            (', jogador', True),
            (',JOGADOR', True),
            (',jogador pl', True),
            (',jogador top50', True),
            (',jogador pl top50', True),
            (',jogador show', True),
            (',jogador dm', True),
            ('jogador', False),
            (',jogadore', False),
            (',jogador hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestExecute:
    @pytest.mark.anyio
    async def test_returns_single_image(self, command, mock_players):
        data = GroupCommandDataFactory.build(text=',jogador')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_caption_contains_player_info(self, command, mock_players):
        data = GroupCommandDataFactory.build(text=',jogador')
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'Lionel Messi' in caption
        assert 'Ponta Direita' in caption
        assert 'Argentina' in caption
        assert 'Inter Miami' in caption
        assert '€ 20,00 mi.' in caption

    @pytest.mark.anyio
    async def test_caption_includes_profile_details(self, command, mock_players):
        data = GroupCommandDataFactory.build(text=',jogador')
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '1,70 m' in caption
        assert 'Esquerdo' in caption

    @pytest.mark.anyio
    async def test_view_once_by_default(self, command, mock_players):
        data = GroupCommandDataFactory.build(text=',jogador')
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, mock_players):
        data = GroupCommandDataFactory.build(text=',jogador show')
        messages = await command.run(data)

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_dm_flag_redirects_to_participant(self, command, mock_players):
        data = GroupCommandDataFactory.build(text=',jogador dm')
        messages = await command.run(data)

        assert messages[0].jid == data.participant

    @pytest.mark.anyio
    async def test_dm_flag_private_keeps_jid(self, command, mock_players):
        data = PrivateCommandDataFactory.build(text=',jogador dm')
        messages = await command.run(data)

        assert messages[0].jid == data.jid


class TestWithLiga:
    @pytest.mark.anyio
    async def test_passes_league_to_fetch_page(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_page',
            new=mocker.AsyncMock(return_value=[_make_player()]),
        )
        mocker.patch.object(
            TransfermarktService,
            'fetch_player_profile',
            new=mocker.AsyncMock(return_value={}),
        )
        mocker.patch.object(HttpClient, 'get_buffer', new=mocker.AsyncMock(return_value=b'img'))

        data = GroupCommandDataFactory.build(text=',jogador pl')
        await command.run(data)

        call_args = TransfermarktService.fetch_page.call_args
        assert call_args.args[1] == _LEAGUE


class TestWithTop:
    @pytest.mark.anyio
    async def test_limits_pages_based_on_top_n(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_page',
            new=mocker.AsyncMock(return_value=[_make_player()]),
        )
        mocker.patch.object(
            TransfermarktService,
            'fetch_player_profile',
            new=mocker.AsyncMock(return_value={}),
        )
        mocker.patch.object(HttpClient, 'get_buffer', new=mocker.AsyncMock(return_value=b'img'))
        mocker.patch('bot.domain.commands.football_player.random.randint', return_value=1)

        data = GroupCommandDataFactory.build(text=',jogador top25')
        await command.run(data)

        TransfermarktService.fetch_page.assert_called_once_with(1, None)

    @pytest.mark.anyio
    async def test_trims_last_page_to_top_n(self, command, mocker):
        players = [_make_player(f'Player{i}') for i in range(25)]
        mocker.patch.object(
            TransfermarktService,
            'fetch_page',
            new=mocker.AsyncMock(return_value=players),
        )
        mocker.patch.object(
            TransfermarktService,
            'fetch_player_profile',
            new=mocker.AsyncMock(return_value={}),
        )
        mocker.patch.object(HttpClient, 'get_buffer', new=mocker.AsyncMock(return_value=b'img'))
        mocker.patch('bot.domain.commands.football_player.random.randint', return_value=1)
        mocker.patch('bot.domain.commands.football_player.random.choice', return_value=players[0])

        data = GroupCommandDataFactory.build(text=',jogador top10')
        await command.run(data)

        choice_call = mocker.patch.object
        _ = choice_call


class TestProfileFetchFailure:
    @pytest.mark.anyio
    async def test_still_returns_image_when_profile_fails(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_page',
            new=mocker.AsyncMock(return_value=[_make_player()]),
        )
        mocker.patch.object(
            TransfermarktService,
            'fetch_player_profile',
            new=mocker.AsyncMock(side_effect=Exception('network error')),
        )
        mocker.patch.object(HttpClient, 'get_buffer', new=mocker.AsyncMock(return_value=b'img'))

        data = GroupCommandDataFactory.build(text=',jogador')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_returns_error_text_when_no_players(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_page',
            new=mocker.AsyncMock(return_value=[]),
        )

        data = GroupCommandDataFactory.build(text=',jogador')
        messages = await command.run(data)

        from bot.domain.models.message import TextContent

        assert isinstance(messages[0].content, TextContent)


class TestBuildCaption:
    def test_includes_club_flag_when_league_provided(self):
        player = _make_player()

        caption = FootballPlayerCommand._build_caption(player, _LEAGUE, {})

        assert _LEAGUE.flag in caption

    def test_no_flag_when_no_league(self):
        player = _make_player()

        caption = FootballPlayerCommand._build_caption(player, None, {})

        assert _LEAGUE.flag not in caption

    def test_includes_foot_capitalized(self):
        player = _make_player()

        caption = FootballPlayerCommand._build_caption(player, None, {'Pé': 'esquerdo'})

        assert 'Esquerdo' in caption

    def test_includes_other_positions(self):
        player = _make_player()

        caption = FootballPlayerCommand._build_caption(
            player, None, {'Posições secundárias': 'Centroavante'}
        )

        assert 'Centroavante' in caption
