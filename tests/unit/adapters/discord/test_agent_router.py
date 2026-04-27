import discord
import pytest

from bot.adapters.discord.agent_router import DiscordAgentRouter


@pytest.fixture
def message(mocker):
    def _build(content: str, *, guild_id: int | None = None):
        msg = mocker.MagicMock(spec=discord.Message)
        msg.author = mocker.MagicMock()
        msg.author.id = 111
        msg.author.__eq__ = mocker.MagicMock(return_value=False)
        msg.content = content
        msg.channel = mocker.MagicMock()
        msg.channel.id = 222
        if guild_id is not None:
            msg.guild = mocker.MagicMock()
            msg.guild.id = guild_id
        else:
            msg.guild = None
        msg.reply = mocker.AsyncMock()
        return msg

    return _build


def _stub_executor(mocker, *, text: str):
    executor_mock = mocker.MagicMock()
    executor_mock.run = mocker.AsyncMock(return_value=mocker.MagicMock(text=text))
    mocker.patch('bot.adapters.discord.agent_router.AgentExecutor', return_value=executor_mock)
    return executor_mock


def _stub_strategy(mocker, *, run_returns):
    strategy_mock = mocker.MagicMock()
    strategy_mock.run = mocker.AsyncMock(return_value=run_returns)
    mocker.patch(
        'bot.adapters.discord.agent_router.CommandRegistry.instance',
        return_value=mocker.MagicMock(get_strategy=mocker.MagicMock(return_value=strategy_mock)),
    )
    return strategy_mock


def _stub_no_strategy(mocker):
    mocker.patch(
        'bot.adapters.discord.agent_router.CommandRegistry.instance',
        return_value=mocker.MagicMock(get_strategy=mocker.MagicMock(return_value=None)),
    )


class TestHandleDm:
    @pytest.mark.anyio
    async def test_runs_agent_then_strategy(self, mocker, message):
        executor_mock = _stub_executor(mocker, text=',table br g4')
        strategy_mock = _stub_strategy(mocker, run_returns=[])
        msg = message('me mande o g4 do Brasileirão')

        router = DiscordAgentRouter()
        await router.handle_dm(msg)

        executor_mock.run.assert_called_once()
        call_data = executor_mock.run.call_args.args[0]
        assert call_data.is_group is False
        assert call_data.platform == 'discord'
        strategy_mock.run.assert_called_once()
        msg.reply.assert_called()
        assert 'resposta' in msg.reply.call_args[0][0]

    @pytest.mark.anyio
    async def test_unknown_command_replies_not_recognized(self, mocker, message):
        _stub_executor(mocker, text=',foo')
        _stub_no_strategy(mocker)
        msg = message('foo bar baz')

        router = DiscordAgentRouter()
        await router.handle_dm(msg)

        msg.reply.assert_called()
        assert 'reconhecido' in msg.reply.call_args[0][0]
