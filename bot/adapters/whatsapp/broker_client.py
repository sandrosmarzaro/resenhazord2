"""WhatsApp operations over the broker.

Writes are fire-and-forget actions published to the ``wa_actions`` queue (the gateway
consumes and applies them via Baileys); only their *failure to publish* is observable,
which matches how the commands use them (they check whether the call threw, not its
return value). Reads (group_metadata) and the on_whatsapp lookup are added alongside as
proactive-push and wa_rpc respectively.
"""

import asyncio
import base64
import json
from typing import Any, ClassVar

from bot.ports.broker_port import BrokerPort


class BrokerWhatsAppClient:
    ACTIONS_QUEUE = 'wa_actions'
    RPC_QUEUE = 'wa_rpc'
    RPC_TIMEOUT_SECONDS: ClassVar[float] = 30.0

    def __init__(self, broker: BrokerPort) -> None:
        self._broker = broker

    async def on_whatsapp(self, jids: list[str]) -> list[dict]:
        return (await self._rpc('on_whatsapp', jids=jids)).get('results', [])

    async def group_metadata(self, jid: str) -> dict:
        return await self._rpc('group_metadata', jid=jid)

    async def download_media(self, message_id: str, source: str) -> bytes:
        # Small media rides base64-inline on the command (Command._get_media prefers it),
        # so this is only reachable for large media — the deferred dedicated media queue.
        message = (
            f'broker download_media unsupported (large media queue pending): {message_id}/{source}'
        )
        raise NotImplementedError(message)

    async def _rpc(self, method: str, **data: Any) -> dict:
        request = json.dumps({'method': method, **data}).encode()
        async with asyncio.timeout(self.RPC_TIMEOUT_SECONDS):
            reply = await self._broker.rpc_call(self.RPC_QUEUE, request)
        return json.loads(reply)

    async def group_participants_update(
        self, jid: str, participants: list[str], action: str
    ) -> list[dict]:
        await self._publish(
            'group_participants_update', jid=jid, participants=participants, action=action
        )
        return []

    async def send_message(self, jid: str, content: dict, options: dict | None = None) -> dict:
        await self._publish('send_message', jid=jid, content=content, options=options)
        return {}

    async def update_profile_picture(self, jid: str, image: bytes) -> None:
        await self._publish(
            'update_profile_picture', jid=jid, image=base64.b64encode(image).decode()
        )

    async def group_update_subject(self, jid: str, subject: str) -> None:
        await self._publish('group_update_subject', jid=jid, subject=subject)

    async def group_update_description(self, jid: str, description: str) -> None:
        await self._publish('group_update_description', jid=jid, description=description)

    async def send_presence_update(self, presence_type: str, jid: str) -> None:
        await self._publish('send_presence_update', type=presence_type, jid=jid)

    async def _publish(self, method: str, **data: Any) -> None:
        action = {'method': method, **data}
        await self._broker.publish(self.ACTIONS_QUEUE, json.dumps(action).encode())
