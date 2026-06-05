import asyncio
import json

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from bot.adapters.http.endpoints.v1.ws import router
from bot.application.command_registry import CommandRegistry
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.dev_list import DevListService


class EchoCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='echo', args=ArgType.OPTIONAL)

    @property
    def menu_description(self) -> str:
        return 'Echoes text'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        return [Reply.to(data).text('Echo')]


class ImageCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='img', args=ArgType.OPTIONAL)

    @property
    def menu_description(self) -> str:
        return 'Sends an image buffer'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        return [Reply.to(data).image_buffer(b'\x89PNG-fake', caption='pic')]


class SlowCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='slow', args=ArgType.OPTIONAL)

    @property
    def menu_description(self) -> str:
        return 'Never finishes on its own'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        await asyncio.sleep(30)
        return [Reply.to(data).text('done')]


def _command_frame(msg_id: str, text: str) -> str:
    return json.dumps(
        {
            'id': msg_id,
            'type': 'command',
            'data': {
                'text': text,
                'jid': 'group@g.us',
                'sender_jid': 'user@s.whatsapp.net',
                'is_group': True,
            },
        }
    )


@pytest.fixture
def client(mocker):
    mocker.patch.object(DevListService, 'is_dev', new=mocker.AsyncMock(return_value=False))
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestWebSocketEndpoint:
    def test_command_roundtrip_acks_then_responds(self, client):
        CommandRegistry.instance().register(EchoCommand())

        with client.websocket_connect('/ws') as ws:
            ws.send_text(_command_frame('m1', ',echo'))
            ack = ws.receive_json()
            response = ws.receive_json()

        assert ack['type'] == 'command_ack'
        assert response['id'] == 'm1'
        assert response['type'] == 'command_response'

    def test_buffer_command_sends_prefixed_binary_frame(self, client):
        CommandRegistry.instance().register(ImageCommand())

        with client.websocket_connect('/ws') as ws:
            ws.send_text(_command_frame('m2', ',img'))
            ws.receive_json()  # ack
            binary = ws.receive_bytes()
            response = ws.receive_json()

        assert binary.startswith(b'm2:')
        assert response['type'] == 'command_response'

    def test_invalid_frame_is_handled_and_connection_survives(self, client):
        CommandRegistry.instance().register(EchoCommand())

        with client.websocket_connect('/ws') as ws:
            ws.send_text('not-json-at-all')
            ws.send_text(_command_frame('m3', ',echo'))
            ack = ws.receive_json()

        assert ack['type'] == 'command_ack'

    def test_disconnect_cancels_in_flight_command(self, client):
        CommandRegistry.instance().register(SlowCommand())

        with client.websocket_connect('/ws') as ws:
            ws.send_text(_command_frame('m4', ',slow'))
            ack = ws.receive_json()
            assert ack['type'] == 'command_ack'
            # leaving the context disconnects while execute() is still sleeping;
            # the endpoint must cancel the in-flight task instead of leaking it.

        with client.websocket_connect('/ws') as ws:
            ws.send_text(_command_frame('m5', ',slow'))
            recovery = ws.receive_json()

        assert recovery['type'] == 'command_ack'
