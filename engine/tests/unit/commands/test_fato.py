import pytest

from bot.domain.commands.fato import FatoCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_json_response


@pytest.fixture
def command():
    return FatoCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', fato', True),
            (',fato', True),
            (', FATO', True),
            (', fato hoje', True),
            (',fato hoje', True),
            ('  , fato  ', True),
            ('fato', False),
            ('hello', False),
            (', fato extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_calls_random_endpoint_by_default(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', fato')
        mock_resp = make_json_response({'text': 'A random fact'})

        mock_get = mocker.patch('bot.domain.commands.fato.HttpClient.get', return_value=mock_resp)
        await command.run(data)

        mock_get.assert_called_once_with('https://uselessfacts.jsph.pl/api/v2/facts/random')

    @pytest.mark.anyio
    async def test_calls_today_endpoint_with_hoje_flag(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', fato hoje')
        mock_resp = make_json_response({'text': 'Today fact'})

        mock_get = mocker.patch('bot.domain.commands.fato.HttpClient.get', return_value=mock_resp)
        await command.run(data)

        mock_get.assert_called_once_with('https://uselessfacts.jsph.pl/api/v2/facts/today')

    @pytest.mark.anyio
    async def test_returns_formatted_text(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', fato')
        mock_resp = make_json_response({'text': 'Cats sleep 70% of their lives.'})

        mocker.patch('bot.domain.commands.fato.HttpClient.get', return_value=mock_resp)
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'FATO' in messages[0].content.text
        assert 'Cats sleep 70% of their lives.' in messages[0].content.text

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', fato', message_id='MSG_42')
        mock_resp = make_json_response({'text': 'A fact'})

        mocker.patch('bot.domain.commands.fato.HttpClient.get', return_value=mock_resp)
        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'

    @pytest.mark.anyio
    async def test_includes_expiration(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', fato', expiration=86400)
        mock_resp = make_json_response({'text': 'A fact'})

        mocker.patch('bot.domain.commands.fato.HttpClient.get', return_value=mock_resp)
        messages = await command.run(data)

        assert messages[0].expiration == 86400
