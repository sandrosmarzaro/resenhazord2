import pytest

from bot.data.football import LEAGUES
from bot.domain.commands.football_player import FootballPlayerCommand
from bot.domain.models.football import PlayerProfile, TmPlayer
from bot.domain.models.message import ImageBufferContent, TextContent
from bot.domain.services.market_dataset import MarketDataset
from bot.infrastructure.http_client import HttpClient
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

_PHOTO = 'https://img.a.transfermarkt.technology/portrait/header/28003.jpg'


def _make_player(name: str = 'Lionel Messi', profile: PlayerProfile | None = None) -> TmPlayer:
    return TmPlayer(
        name=name,
        position='Right Winger',
        age=36,
        nationality='Argentina',
        club='Inter Miami',
        club_id='50251',
        market_value=20_000_000,
        photo_url=_PHOTO,
        badge_url='https://tmssl.akamaized.net/images/wappen/head/50251.png',
        nationality_flag_emoji='🇦🇷',
        profile=profile
        or PlayerProfile(
            birth_city='Rosario', birth_country='Argentina', height_cm='170', foot='left'
        ),
    )


@pytest.fixture
def command():
    return FootballPlayerCommand()


@pytest.fixture
def photo(mocker):
    return mocker.patch.object(
        HttpClient, 'get_buffer', new=mocker.AsyncMock(return_value=b'fake-photo')
    )


@pytest.fixture
def dataset(mocker, photo):
    def mount(players: list[TmPlayer]):
        fetch = mocker.AsyncMock(return_value=players)
        mocker.patch.object(MarketDataset, 'players', new=fetch)
        return fetch

    return mount


@pytest.fixture
def pick_first(mocker):
    return mocker.patch(
        'bot.domain.commands.football_player.random.choice', side_effect=lambda pool: pool[0]
    )


async def _caption(command, text: str = ',jogador') -> str:
    messages = await command.run(GroupCommandDataFactory.build(text=text))
    return messages[0].content.caption


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',jogador', True),
            (', jogador', True),
            (',JOGADOR', True),
            (',jogador pl', True),
            (',jogador ar', True),
            (',jogador top50', True),
            (',jogador pl top50', True),
            (',jogador show', True),
            (',jogador dm', True),
            (',jogador uy', False),
            ('jogador', False),
            (',jogadore', False),
            (',jogador hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestReply:
    @pytest.mark.anyio
    async def test_sends_player_photo(self, command, dataset, photo):
        dataset([_make_player()])

        messages = await command.run(GroupCommandDataFactory.build(text=',jogador'))

        assert isinstance(messages[0].content, ImageBufferContent)
        photo.assert_awaited_once_with(_PHOTO)

    @pytest.mark.anyio
    async def test_caption_describes_player_in_portuguese(self, command, dataset):
        dataset([_make_player()])

        caption = await _caption(command)

        assert caption == (
            '*Lionel Messi* — Ponta Direita\n'
            '\n'
            '🎂 36 anos   🇦🇷 Argentina\n'
            '🇦🇷 Rosario, Argentina\n'
            '🏟️ Inter Miami \n'
            '📏 1,70 m   👟 Esquerdo\n'
            '\n'
            '💰 € 20,00 mi.'
        )

    @pytest.mark.anyio
    async def test_missing_profile_details_are_skipped(self, command, dataset):
        dataset([_make_player(profile=PlayerProfile())])

        caption = await _caption(command)

        assert ('📏' not in caption, '👟' not in caption, 'Rosario' not in caption) == (
            True,
            True,
            True,
        )

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('profile', 'line'),
        [
            (PlayerProfile(height_cm='185'), '📏 1,85 m'),
            (PlayerProfile(foot='both'), '👟 Ambidestro'),
            (PlayerProfile(birth_city='Leeds'), '📍 Leeds'),
        ],
    )
    async def test_partial_profile_shows_what_it_has(self, command, dataset, profile, line):
        dataset([_make_player(profile=profile)])

        caption = await _caption(command)

        assert line in caption.splitlines()

    @pytest.mark.anyio
    async def test_no_players_replies_with_text(self, command, dataset):
        dataset([])

        messages = await command.run(GroupCommandDataFactory.build(text=',jogador'))

        assert isinstance(messages[0].content, TextContent)

    @pytest.mark.anyio
    async def test_view_once_by_default(self, command, dataset):
        dataset([_make_player()])

        messages = await command.run(GroupCommandDataFactory.build(text=',jogador'))

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, dataset):
        dataset([_make_player()])

        messages = await command.run(GroupCommandDataFactory.build(text=',jogador show'))

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_dm_flag_redirects_to_participant(self, command, dataset):
        dataset([_make_player()])
        data = GroupCommandDataFactory.build(text=',jogador dm')

        messages = await command.run(data)

        assert messages[0].jid == data.participant

    @pytest.mark.anyio
    async def test_dm_flag_private_keeps_jid(self, command, dataset):
        dataset([_make_player()])
        data = PrivateCommandDataFactory.build(text=',jogador dm')

        messages = await command.run(data)

        assert messages[0].jid == data.jid


class TestPool:
    @pytest.mark.anyio
    async def test_global_pool_is_the_most_valuable(self, command, dataset, pick_first):
        fetch = dataset([_make_player(f'P{i}') for i in range(1200)])

        await command.run(GroupCommandDataFactory.build(text=',jogador'))

        fetch.assert_awaited_once_with('')
        assert len(pick_first.call_args.args[0]) == FootballPlayerCommand.GLOBAL_POOL

    @pytest.mark.anyio
    async def test_league_pool_uses_dataset_league_id(self, command, dataset, pick_first):
        fetch = dataset([_make_player(f'P{i}') for i in range(150)])

        caption = await _caption(command, ',jogador ar')

        fetch.assert_awaited_once_with('ARG1')
        assert len(pick_first.call_args.args[0]) == FootballPlayerCommand.LEAGUE_POOL
        assert LEAGUES['ar'].flag in caption

    @pytest.mark.anyio
    async def test_top_n_limits_pool(self, command, dataset, pick_first):
        players = [_make_player(f'P{i}') for i in range(5)]
        dataset(players)

        await command.run(GroupCommandDataFactory.build(text=',jogador top2'))

        pick_first.assert_called_once_with(players[:2])

    @pytest.mark.anyio
    async def test_top_zero_falls_back_to_default_pool(self, command, dataset, pick_first):
        dataset([_make_player(f'P{i}') for i in range(1200)])

        await command.run(GroupCommandDataFactory.build(text=',jogador top0'))

        assert len(pick_first.call_args.args[0]) == FootballPlayerCommand.GLOBAL_POOL
