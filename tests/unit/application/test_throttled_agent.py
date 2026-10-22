import pytest

from bot.application.throttled_agent import ThrottledAgent
from bot.domain.models.command_data import CommandData


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def agent(mocker):
    agent = mocker.Mock()
    agent.run = mocker.AsyncMock(return_value=_dm(',carro'))
    return agent


def _limiter(mocker, *, allowed: bool):
    limiter = mocker.Mock()
    limiter.allow = mocker.AsyncMock(return_value=allowed)
    return limiter


def _dm(text: str) -> CommandData:
    return CommandData(
        text=text, jid='user@s.whatsapp.net', sender_jid='user@s.whatsapp.net', is_group=False
    )


class TestRun:
    @pytest.mark.anyio
    async def test_limited_conversation_gets_no_agent_turn(self, agent, mocker):
        throttled = ThrottledAgent(agent, _limiter(mocker, allowed=False))

        result = await throttled.run(_dm('Entendi o que você precisa'))

        assert result is None
        agent.run.assert_not_awaited()

    @pytest.mark.anyio
    async def test_allowed_conversation_runs_the_agent(self, agent, mocker):
        throttled = ThrottledAgent(agent, _limiter(mocker, allowed=True))

        result = await throttled.run(_dm('me manda um carro'))

        assert result == _dm(',carro')

    @pytest.mark.anyio
    async def test_limits_per_chat_and_sender(self, agent, mocker):
        limiter = _limiter(mocker, allowed=True)
        data = CommandData(
            text='@resenhazord placar',
            jid='group@g.us',
            sender_jid='user@s.whatsapp.net',
            participant='member@lid',
            is_group=True,
        )

        await ThrottledAgent(agent, limiter).run(data)

        limiter.allow.assert_awaited_once_with('group@g.us:member@lid')

    @pytest.mark.anyio
    async def test_runs_unlimited_without_a_limiter(self, agent):
        result = await ThrottledAgent(agent, None).run(_dm('me manda um carro'))

        assert result == _dm(',carro')
