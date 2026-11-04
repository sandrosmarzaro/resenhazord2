import asyncio
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import structlog

from bot.adapters.broker.command_consumer import CommandConsumer
from bot.domain.commands.ban import BanCommand
from bot.domain.models.command_data import CommandData
from bot.infrastructure.broker import RabbitBroker

BOT_JID = '5500000000001@s.whatsapp.net'
OWNER_JID = '5527900000001@s.whatsapp.net'
ADMIN_JID = '5527900000002@s.whatsapp.net'
MEMBER_JID = '5527900000003@s.whatsapp.net'
OTHER_JID = '5527900000004@s.whatsapp.net'
GROUP_A = '120000000000000001@g.us'
GROUP_B = '120000000000000002@g.us'

# Containers publish their ports on the docker host. Anything else means a URL came from
# .env, which points at the production Mongo, and the suite must stop before using it.
LOCAL_HOSTS = frozenset({'localhost', '127.0.0.1', '::1'})
REPLY_TIMEOUT_SECONDS = 15


def assert_local(url: str) -> None:
    host = urlparse(url).hostname
    if host not in LOCAL_HOSTS:
        msg = f'refusing to run against a non-local host: {host}'
        raise RuntimeError(msg)


def participant(jid: str, *, admin: str | None = None) -> dict[str, Any]:
    return {'id': jid, 'admin': admin}


def group_metadata(*participants: dict[str, Any], owner: str = OWNER_JID) -> dict[str, Any]:
    return {'participants': list(participants), 'owner': owner, 'subject': 'Resenha'}


@dataclass
class Watched:
    """A list whose waiters wake on every append instead of polling."""

    items: list[dict[str, Any]] = field(default_factory=list)
    _changed: asyncio.Event = field(default_factory=asyncio.Event)

    def append(self, item: dict[str, Any]) -> None:
        self.items.append(item)
        self._changed.set()

    async def wait_for(self, predicate: Callable[[list[dict[str, Any]]], bool]) -> None:
        async with asyncio.timeout(REPLY_TIMEOUT_SECONDS):
            while not predicate(self.items):
                self._changed.clear()
                await self._changed.wait()


class Collected(Watched):
    async def capture(self, body: bytes) -> None:
        self.append(json.loads(body))

    def by_id(self, correlation_id: str) -> list[dict[str, Any]]:
        return [body for body in self.items if body['id'] == correlation_id]


class LogRecorder(Watched):
    def __call__(self, logger: Any, method: str, event: dict[str, Any]) -> dict[str, Any]:
        self.append(event)
        raise structlog.DropEvent

    def events(self) -> list[str]:
        return [item['event'] for item in self.items]


class BotUnderTest:
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker
        self.replies = Collected()
        self.dead_letters = Collected()
        self.logs = LogRecorder()

    async def start(self, consumer: CommandConsumer) -> None:
        await consumer.start()
        await self._broker.consume(CommandConsumer.REPLIES_QUEUE, self.replies.capture)
        await self._broker.consume(CommandConsumer.DLQ_QUEUE, self.dead_letters.capture)

    @staticmethod
    def envelope(text: str, **fields: Any) -> dict[str, Any]:
        sender = fields.pop('sender', MEMBER_JID)
        data = {
            'text': text,
            'jid': fields.pop('jid', GROUP_A),
            'sender_jid': sender,
            'participant': sender,
            'is_group': True,
            'message_id': fields.pop('message_id', uuid.uuid4().hex),
            'mentioned_jids': fields.pop('mentioned', []),
            **fields,
        }
        return {'id': uuid.uuid4().hex, 'data': data}

    async def publish(self, envelope: dict[str, Any]) -> None:
        await self._broker.publish(CommandConsumer.COMMANDS_QUEUE, json.dumps(envelope).encode())

    async def reply_to(self, envelope: dict[str, Any]) -> dict[str, Any]:
        await self.replies.wait_for(lambda _: bool(self.replies.by_id(envelope['id'])))
        return self.replies.by_id(envelope['id'])[0]

    async def send(self, text: str, **fields: Any) -> dict[str, Any]:
        envelope = self.envelope(text, **fields)
        await self.publish(envelope)
        return await self.reply_to(envelope)


def texts(reply: dict[str, Any]) -> list[str]:
    return [message['content'].get('text', '') for message in reply['messages']]


class FakeWhatsApp:
    """Stands in for the WhatsApp port in a child process, where mocks don't travel."""

    def __init__(self, metadata: dict[str, Any]) -> None:
        self._metadata = metadata

    async def group_metadata(self, jid: str) -> dict[str, Any]:
        return self._metadata

    async def group_participants_update(self, jid: str, jids: list[str], action: str) -> list:
        return []


def ban_in_a_group_of_only_bot_and_owner() -> None:
    metadata = group_metadata(
        participant(BOT_JID, admin='admin'), participant(OWNER_JID, admin='superadmin')
    )
    command = BanCommand(bot_jid=BOT_JID, whatsapp=FakeWhatsApp(metadata))
    data = CommandData(
        text=',ban', jid=GROUP_A, sender_jid=OWNER_JID, participant=OWNER_JID, is_group=True
    )
    asyncio.run(command.run(data))
