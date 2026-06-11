"""WhatsApp operations over the broker.

Writes are fire-and-forget actions published to the ``wa_actions`` queue (the gateway
consumes and applies them via Baileys); only their *failure to publish* is observable,
which matches how the commands use them (they check whether the call threw, not its
return value). Reads (group_metadata) and the on_whatsapp lookup are added alongside as
proactive-push and wa_rpc respectively.
"""

import base64
import json
from typing import Any

from bot.ports.broker_port import BrokerPort


class BrokerWhatsAppClient:
    ACTIONS_QUEUE = 'wa_actions'

    def __init__(self, broker: BrokerPort) -> None:
        self._broker = broker

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
