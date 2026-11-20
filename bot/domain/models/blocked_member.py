from dataclasses import dataclass
from typing import ClassVar, Self

from bot.domain.dev_key import DevKey
from bot.domain.jid import normalize_jid, normalize_jids
from bot.domain.models.command_data import CommandData


@dataclass(frozen=True)
class BlockedMember:
    # WhatsApp names one member by LID or by phone number, and the core can't map one to
    # the other. A member keeps both forms, so a block set through one matches the other.
    key: str
    alt_key: str | None = None

    _PHONE_NUMBER_SUFFIX: ClassVar[str] = '@s.whatsapp.net'

    @property
    def keys(self) -> frozenset[str]:
        return frozenset(key for key in (self.key, self.alt_key) if key)

    @classmethod
    def of_participant(cls, entry: dict) -> Self:
        forms = normalize_jids((entry['id'], entry.get('phoneNumber'), entry.get('lid')))
        key = next((form for form in forms if form.endswith(cls._PHONE_NUMBER_SUFFIX)), forms[0])
        alt_key = next((form for form in forms if form != key), None)
        return cls(key=key, alt_key=alt_key)

    @classmethod
    def of_sender(cls, data: CommandData) -> Self:
        # A LID-addressed group sends the phone number as sender_jid and the LID as
        # participant, so the sender matches a block stored under either form.
        alt_key = normalize_jid(data.participant) if data.participant else None
        return cls(key=normalize_jid(DevKey.of(data)), alt_key=alt_key)
