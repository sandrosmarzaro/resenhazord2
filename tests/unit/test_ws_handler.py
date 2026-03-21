import json

import pytest

from bot.adapters.http.ws_handler import WebSocketHandler
from bot.application.command_handler import CommandHandler
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class EchoCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='echo', args=ArgType.OPTIONAL)

    @property
    def menu_description(self) -> str:
        return 'Echoes text'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        from bot.domain.builders.reply import Reply

        return [Reply.to(data).text(f'Echo: {parsed.rest or "nothing"}')]


@pytest.fixture
def mock_ws(mocker):
    ws = mocker.AsyncMock()
    ws.send_json = mocker.AsyncMock()
    ws.send_bytes = mocker.AsyncMock()
    return ws


@pytest.fixture
def handler(mock_ws):
    registry = CommandRegistry.instance()
    registry.register(EchoCommand())
    return WebSocketHandler(mock_ws, CommandHandler(registry))


class TestWebSocketHandlerCommand:
    @pytest.mark.anyio
    async def test_command_match_returns_response(self, mock_ws, handler):
        msg = json.dumps(
            {
                'id': 'test-1',
                'type': 'command',
                'data': {
                    'text': ',echo hello',
                    'jid': 'group@g.us',
                    'sender_jid': 'user@s.whatsapp.net',
                    'is_group': True,
                },
            }
        )

        await handler.handle_message(msg)

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args['id'] == 'test-1'
        assert call_args['type'] == 'command_response'
        assert len(call_args['data']['messages']) == 1
        assert call_args['data']['messages'][0]['content']['text'] == 'Echo: hello'

    @pytest.mark.anyio
    async def test_no_match_returns_no_match(self, mock_ws, handler):
        msg = json.dumps(
            {
                'id': 'test-2',
                'type': 'command',
                'data': {
                    'text': ',unknown',
                    'jid': 'group@g.us',
                    'sender_jid': 'user@s.whatsapp.net',
                },
            }
        )

        await handler.handle_message(msg)

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args['type'] == 'no_match'


class TestWebSocketHandlerWaResult:
    @pytest.mark.anyio
    async def test_wa_result_resolves_future(self, mock_ws, handler):
        import asyncio

        # Only run on asyncio backend since wa_call uses asyncio.Future
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pytest.skip('asyncio-only test')
            return

        future: asyncio.Future = loop.create_future()
        handler._pending['call-1'] = future
        msg = json.dumps(
            {
                'id': 'call-1',
                'type': 'wa_result',
                'data': {'participants': ['user1']},
            }
        )

        await handler.handle_message(msg)

        assert future.done()
        assert future.result() == {'participants': ['user1']}
