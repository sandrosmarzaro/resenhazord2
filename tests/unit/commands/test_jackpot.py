import pytest

from bot.domain.commands.jackpot import JackpotCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


@pytest.fixture
def command():
    return JackpotCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', jackpot', True),
            (',jackpot', True),
            (', JACKPOT', True),
            (', slot', True),
            (',slot', True),
            (', caçaníqueis', True),
            (', cacaniqueis', True),
            ('  , jackpot  ', True),
            ('jackpot', False),
            (', jackpot extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_single_text_message(self, command):
        data = GroupCommandDataFactory.build(text=', jackpot')

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)

    @pytest.mark.anyio
    async def test_output_contains_slot_frame(self, command):
        data = GroupCommandDataFactory.build(text=', jackpot')

        messages = await command.run(data)

        text = messages[0].content.text
        assert '🎰 *JACKPOT* 🎰' in text
        assert '╔' in text
        assert '╚' in text

    @pytest.mark.anyio
    async def test_jackpot_on_three_matching(self, command, mocker):
        mocker.patch('bot.domain.commands.jackpot.random.choices', return_value=['💎', '💎', '💎'])
        data = GroupCommandDataFactory.build(text=', jackpot')

        messages = await command.run(data)

        assert 'JACKPOT!' in messages[0].content.text

    @pytest.mark.anyio
    async def test_partial_win_on_two_matching(self, command, mocker):
        mocker.patch('bot.domain.commands.jackpot.random.choices', return_value=['💎', '💎', '🍒'])
        data = GroupCommandDataFactory.build(text=', jackpot')

        messages = await command.run(data)

        assert 'Quase lá!' in messages[0].content.text

    @pytest.mark.anyio
    async def test_loss_on_no_matching(self, command, mocker):
        mocker.patch('bot.domain.commands.jackpot.random.choices', return_value=['💎', '🍒', '🍋'])
        data = GroupCommandDataFactory.build(text=', jackpot')

        messages = await command.run(data)

        assert 'Tente novamente!' in messages[0].content.text

    @pytest.mark.anyio
    async def test_works_in_private_chat(self, command):
        data = PrivateCommandDataFactory.build(text=', jackpot')

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].jid == data.jid

    @pytest.mark.anyio
    async def test_includes_expiration(self, command):
        data = GroupCommandDataFactory.build(text=', jackpot', expiration=86400)

        messages = await command.run(data)

        assert messages[0].expiration == 86400

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command):
        data = GroupCommandDataFactory.build(text=', jackpot', message_id='MSG_42')

        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'
