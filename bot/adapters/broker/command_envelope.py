import base64
from typing import Any

from bot.adapters.http.schemas import CommandPayload
from bot.domain.commands.base import Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class CommandEnvelope:
    @staticmethod
    def to_command_data(data: dict[str, Any]) -> CommandData:
        parsed = CommandPayload.model_validate(data)
        buffer = data.get('media_buffer_b64')
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
            message_id=parsed.message_id,
            push_name=parsed.push_name,
            platform=Platform.WHATSAPP,
        )

    @classmethod
    def reply(cls, envelope_id: str, messages: list[BotMessage]) -> dict[str, Any]:
        return {'id': envelope_id, 'messages': [cls._serialize(message) for message in messages]}

    @staticmethod
    def _serialize(message: BotMessage) -> dict[str, Any]:
        payload = message.to_dict()
        if message.content.has_buffer:
            # Small media rides base64-inline in the reply JSON (the WS path sent it as a
            # separate binary frame); the gateway decodes it back in ReplyDeserializer.
            # has_buffer guarantees .buffer exists but the union can't be narrowed on it.
            buffer = message.content.buffer  # type: ignore[union-attr]
            payload['content']['buffer_b64'] = base64.b64encode(buffer).decode()
        return payload
