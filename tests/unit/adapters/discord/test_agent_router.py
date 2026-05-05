import discord
import pytest

from bot.adapters.discord.agent_router import DiscordAgentRouter
from bot.adapters.discord.renderer import DiscordReply
from bot.domain.models.command_data import CommandData
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.message import BotMessage


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


class TestBuiltinPrefix:
    @pytest.mark.anyio
    async def test_clarify_prefix_replies_message(self, mocker, message):
        _stub_executor(mocker, text=',clarify:IA indisponível. Use o menu')
        _stub_no_strategy(mocker)
        msg = message('oi')

        router = DiscordAgentRouter()
        await router.handle_dm(msg)

        msg.reply.assert_called()
        assert 'IA indisponível' in msg.reply.call_args[0][0]

    @pytest.mark.anyio
    async def test_suggest_prefix_replies_suggestion(self, mocker, message):
        _stub_executor(mocker, text=',suggest:Tente usar ,time')
        _stub_no_strategy(mocker)
        msg = message('oi')

        router = DiscordAgentRouter()
        await router.handle_dm(msg)

        msg.reply.assert_called()
        assert 'Tente' in msg.reply.call_args[0][0]

    @pytest.mark.anyio
    async def test_clarify_prefix_suppresses_mentions(self, mocker, message):
        _stub_executor(mocker, text=',clarify:check @everyone')
        _stub_no_strategy(mocker)
        msg = message('oi')

        router = DiscordAgentRouter()
        await router.handle_dm(msg)

        allowed = msg.reply.call_args[1]['allowed_mentions']
        assert allowed.everyone is False
        assert allowed.users is False
        assert allowed.roles is False

    @pytest.mark.anyio
    async def test_suggest_prefix_suppresses_mentions(self, mocker, message):
        _stub_executor(mocker, text=',suggest:try @here')
        _stub_no_strategy(mocker)
        msg = message('oi')

        router = DiscordAgentRouter()
        await router.handle_dm(msg)

        allowed = msg.reply.call_args[1]['allowed_mentions']
        assert allowed.everyone is False
        assert allowed.users is False
        assert allowed.roles is False


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


class TestHandleMention:
    @pytest.mark.anyio
    async def test_mention_dispatches_with_group_flag(self, mocker, message):
        executor_mock = _stub_executor(mocker, text=',d20')
        _stub_strategy(mocker, run_returns=[])
        msg = message('<@bot> roll', guild_id=456)

        router = DiscordAgentRouter()
        await router.handle_mention(msg)

        executor_call_data = executor_mock.run.call_args.args[0]
        assert executor_call_data.is_group is True


class TestDispatchException:
    @pytest.mark.anyio
    async def test_generic_exception_replies_error(self, mocker, message):
        executor_mock = mocker.MagicMock()
        executor_mock.run = mocker.AsyncMock(side_effect=RuntimeError('boom'))
        mocker.patch('bot.adapters.discord.agent_router.AgentExecutor', return_value=executor_mock)
        mocker.patch(
            'bot.adapters.discord.agent_router.CommandRegistry.instance',
            return_value=mocker.MagicMock(),
        )
        msg = message('test')

        router = DiscordAgentRouter()
        await router._dispatch(msg, mocker.MagicMock())

        msg.reply.assert_called()
        assert 'Erro' in msg.reply.call_args[0][0]


class TestRunPipeline:
    @pytest.mark.anyio
    async def test_renders_and_sends_non_empty_messages(self, mocker, message):
        _stub_executor(mocker, text=',pub')
        bot_msg = BotMessage(jid='test', content=TextContent(text='hello'))
        _stub_strategy(mocker, run_returns=[bot_msg])

        renderer_mock = mocker.MagicMock()
        renderer_mock.render_async = mocker.AsyncMock(
            return_value=DiscordReply(text='hello', embed=None, file=None)
        )
        msg = message('test')
        data = CommandData(text=',pub', jid='1', sender_jid='2', is_group=False, platform='discord')

        router = DiscordAgentRouter(renderer=renderer_mock)
        await router._run_pipeline(msg, data)

        renderer_mock.render_async.assert_called_once_with(bot_msg)


class TestSendReply:
    @pytest.mark.anyio
    async def test_text_only_reply_suppresses_mentions(self, mocker, message):
        msg = message('test')
        router = DiscordAgentRouter()

        await router._send_reply(msg, DiscordReply(text='hello', embed=None, file=None))

        msg.reply.assert_called_once()
        assert msg.reply.call_args[0][0] == 'hello'
        allowed = msg.reply.call_args[1]['allowed_mentions']
        assert allowed.everyone is False
        assert allowed.users is False
        assert allowed.roles is False

    @pytest.mark.anyio
    async def test_empty_text_uses_placeholder(self, mocker, message):
        msg = message('test')
        router = DiscordAgentRouter()

        await router._send_reply(msg, DiscordReply(text=None, embed=mocker.MagicMock(), file=None))

        sent_text = msg.reply.call_args[0][0]
        assert sent_text == DiscordAgentRouter.EMPTY_TEXT_PLACEHOLDER

    @pytest.mark.anyio
    async def test_reply_with_file(self, mocker, message):
        msg = message('test')
        file_mock = mocker.MagicMock()
        router = DiscordAgentRouter()

        await router._send_reply(msg, DiscordReply(text='see attached', embed=None, file=file_mock))

        kwargs = msg.reply.call_args[1]
        assert kwargs['file'] is file_mock

    @pytest.mark.anyio
    async def test_reply_with_embed(self, mocker, message):
        msg = message('test')
        embed_mock = mocker.MagicMock()
        router = DiscordAgentRouter()

        await router._send_reply(msg, DiscordReply(text=None, embed=embed_mock, file=None))

        kwargs = msg.reply.call_args[1]
        assert kwargs['embed'] is embed_mock


class TestGroupData:
    def test_group_data_sets_is_group_true(self, message):
        msg = message('hello', guild_id=123)

        data = DiscordAgentRouter._group_data(msg)

        assert data.is_group is True
        assert data.platform == 'discord'
        assert str(msg.channel.id) == data.jid
