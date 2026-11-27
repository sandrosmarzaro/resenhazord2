import base64
import secrets
from typing import Any, ClassVar

from bot.adapters.http.schemas import CommandPayload
from bot.domain.commands.base import Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class CommandEnvelope:
    # Baileys' own outgoing ids are 3EB0 and 18 uppercase hex digits; ours match them.
    _MESSAGE_ID_PREFIX: ClassVar[str] = '3EB0'
    _MESSAGE_ID_BYTES: ClassVar[int] = 9

    @staticmethod
    def to_command_data(data: dict[str, Any]) -> CommandData:
        parsed = CommandPayload.model_validate(data)
        buffer = data.get('media_buffer_b64')
        audio = data.get('media_audio_b64')
        return CommandData(
            text=parsed.text,
            jid=parsed.jid,
            sender_jid=parsed.sender_jid,
            participant=parsed.participant,
            is_group=parsed.is_group,
            expiration=parsed.expiration,
            mentioned_jids=parsed.mentioned_jids,
            quoted_message_id=parsed.quoted_message_id,
            quoted_text=parsed.quoted_text,
            media_type=parsed.media_type,
            media_source=parsed.media_source,
            media_is_animated=parsed.media_is_animated,
            media_caption=parsed.media_caption,
            media_buffer=base64.b64decode(buffer) if buffer else None,
            media_audio=base64.b64decode(audio) if audio else None,
            message_id=parsed.message_id,
            push_name=parsed.push_name,
            platform=Platform.WHATSAPP,
        )

    @classmethod
    def reply(cls, envelope_id: str, messages: list[BotMessage]) -> dict[str, Any]:
        return {'id': envelope_id, 'messages': [cls._serialize(message) for message in messages]}

    @classmethod
    def _serialize(cls, message: BotMessage) -> dict[str, Any]:
        payload = message.to_dict()
        # The core names each chat reply, so the record of the command that made it is
        # found again when a dev quotes it with ,bug. A status leaves the chat, so it
        # gets none. An older gateway ignores the field and Baileys names it instead.
        if not message.group_status:
            payload['message_id'] = (
                cls._MESSAGE_ID_PREFIX + secrets.token_hex(cls._MESSAGE_ID_BYTES).upper()
            )
        if message.content.has_buffer:
            # Small media rides base64-inline in the reply JSON (the WS path sent it as a
            # separate binary frame); the gateway decodes it back in ReplyDeserializer.
            # has_buffer guarantees .buffer exists but the union can't be narrowed on it.
            buffer = message.content.buffer  # type: ignore[union-attr]
            payload['content']['buffer_b64'] = base64.b64encode(buffer).decode()
        return payload
