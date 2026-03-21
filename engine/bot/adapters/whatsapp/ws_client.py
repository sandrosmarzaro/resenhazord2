"""WhatsApp operations via WebSocket — sends wa_call, awaits wa_result."""

import asyncio
import base64
import uuid
from typing import Any

from bot.adapters.http.ws_handler import WebSocketHandler

MEDIA_TIMEOUT = 60.0


class WhatsAppWsClient:
    """Implements WhatsAppPort by delegating to the TS side over WebSocket."""

    def __init__(self, handler: WebSocketHandler) -> None:
        self._handler = handler

    async def _call(
        self, method: str, data: dict[str, Any], deadline: float = 30.0
    ) -> dict[str, Any]:
        return await self._handler.call_whatsapp(method, data, deadline=deadline)

    async def group_metadata(self, jid: str) -> dict:
        return await self._call('group_metadata', {'jid': jid})

    async def group_participants_update(
        self, jid: str, participants: list[str], action: str
    ) -> list[dict]:
        result = await self._call(
            'group_participants_update',
            {'jid': jid, 'participants': participants, 'action': action},
        )
        return result.get('results', [])

    async def on_whatsapp(self, jids: list[str]) -> list[dict]:
        result = await self._call('on_whatsapp', {'jids': jids})
        return result.get('results', [])

    async def send_message(self, jid: str, content: dict, options: dict | None = None) -> dict:
        return await self._call(
            'send_message', {'jid': jid, 'content': content, 'options': options}
        )

    async def update_profile_picture(self, jid: str, image: bytes) -> None:
        msg_id = str(uuid.uuid4())
        future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        self._handler._pending[msg_id] = future
        await self._handler._ws.send_json(
            {
                'id': msg_id,
                'type': 'wa_call',
                'method': 'update_profile_picture',
                'data': {'jid': jid},
            }
        )
        await self._handler._ws.send_bytes(image)
        await asyncio.wait_for(future, timeout=30.0)

    async def group_update_subject(self, jid: str, subject: str) -> None:
        await self._call('group_update_subject', {'jid': jid, 'subject': subject})

    async def group_update_description(self, jid: str, description: str) -> None:
        await self._call('group_update_description', {'jid': jid, 'description': description})

    async def send_presence_update(self, presence_type: str, jid: str) -> None:
        await self._call('send_presence_update', {'type': presence_type, 'jid': jid})

    async def download_media(self, message_id: str, source: str) -> bytes:
        result = await self._call(
            'download_media',
            {'message_id': message_id, 'source': source},
            deadline=MEDIA_TIMEOUT,
        )
        return base64.b64decode(result['buffer'])
