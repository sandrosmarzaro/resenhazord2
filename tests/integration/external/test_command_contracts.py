import httpx
import pytest
from structlog.testing import capture_logs

from bot.application.command_registry import CommandRegistry
from bot.application.register_commands import register_all_commands
from bot.settings import Settings
from tests.factories.command_data import GroupCommandDataFactory

pytestmark = pytest.mark.external


# Not flaky: moneyconvert answers 403 to GitHub's runners every night and 200 to the core
# node, so a retry can't help. Only an HTTP error is tolerated, so a changed response
# still fails, and the test still passes wherever the upstream answers.
_BLOCKS_THE_RUNNER = pytest.mark.xfail(
    raises=httpx.HTTPStatusError, strict=False, reason='the upstream blocks GitHub runners'
)


def _call(text: str, needs: str = '', *marks: pytest.Mark) -> object:
    return pytest.param(text, needs, id=text, marks=marks)


# One real invocation per upstream a command reaches, with the setting its key lives
# in. A command passes when it replies without logging an error or upstream_failed,
# the event every swallowed upstream failure logs. The ,dl videos need the core
# node's login cookies; the photo-only tweet goes through FxTwitter without them.
_CALLS = [
    _call(',alcorão'),
    _call(',animal'),
    _call(',áudio bom dia'),
    _call(',carta'),
    _call(',bicho'),
    _call(',carro'),
    _call(',carro wiki'),
    _call(',cr'),
    _call(',cr deck'),
    _call(',moeda', '', _BLOCKS_THE_RUNNER),
    _call(',fato'),
    _call(',fato hoje'),
    _call(',fipe'),
    _call(',jogador'),
    _call(',jogador fifa'),
    _call(',tabela'),
    _call(',time'),
    _call(',time fifa'),
    _call(',horóscopo áries'),
    _call(',fuck @5511999999999'),
    _call(',lol'),
    _call(',lol build'),
    _call(',mtg'),
    _call(',mtg booster'),
    _call(',comida'),
    _call(',anime'),
    _call(',manga'),
    _call(',pokémon'),
    _call(',pokémon team'),
    _call(',pokémontcg'),
    _call(',pokémontcg booster'),
    _call(',placar'),
    _call(',porno'),
    _call(',porno ia'),
    _call(',puppy'),
    _call(',rule 34'),
    _call(',torá'),
    _call(',ygo'),
    _call(',ygo booster'),
    _call(',bíblia'),
    _call(',bandeira', 'restcountries_api_key'),
    _call(',bandeira detail', 'restcountries_api_key'),
    _call(',filme', 'tmdb_api_key'),
    _call(',filme tmdb', 'tmdb_api_key'),
    _call(',série', 'tmdb_api_key'),
    _call(',game', 'twitch_client_id'),
    _call(',hs', 'bnet_id'),
    _call(',hs booster', 'bnet_id'),
    _call(',hentai'),
    _call(',hentai ehentai'),
    _call(',hentai hitomi'),
    _call(',hentai nhentai'),
    _call(',música'),
    _call(',música free', 'jamendo_client_id'),
    _call(',cerveja'),
    _call(',dl https://x.com/captainamerica/status/719944021058060289', 'ytdlp_cookies'),
    _call(',dl https://www.instagram.com/reel/CDUMkliABpa/', 'ytdlp_cookies'),
    _call(',dl https://x.com/TheEllenShow/status/440322224407314432'),
]


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def registry(mocker, mock_whatsapp, settings) -> CommandRegistry:
    # The agent graph is not under test and would dial Redis and the LLM providers.
    mocker.patch('bot.application.register_commands.build_agent_graph')
    register_all_commands(settings)
    registry = CommandRegistry.instance()
    registry.set_whatsapp(mock_whatsapp)
    return registry


@pytest.mark.anyio
@pytest.mark.parametrize(('text', 'needs'), _CALLS)
async def test_command_replies_from_its_upstream(registry, settings, text, needs):
    if needs and not getattr(settings, needs):
        pytest.skip(f'{needs.upper()} not set')
    command = registry.get_strategy(text)
    data = GroupCommandDataFactory.build(text=text)

    with capture_logs() as logs:
        messages = await command.run(data)

    failures = [
        log for log in logs if log['event'] == 'upstream_failed' or log['log_level'] == 'error'
    ]
    assert messages
    assert failures == []
