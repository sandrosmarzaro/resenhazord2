import string
import unicodedata
from enum import StrEnum

from bot.data.agent_replies import CONFIRM_REPLIES, DENY_REPLIES, EMOJI_MODIFIERS


class ConfirmationReply(StrEnum):
    YES = 'yes'
    NO = 'no'
    OTHER = 'other'

    @classmethod
    def classify(cls, text: str) -> ConfirmationReply:
        normalized = cls._normalize(text)
        if normalized in CONFIRM_REPLIES:
            return cls.YES
        if normalized in DENY_REPLIES:
            return cls.NO
        return cls.OTHER

    @staticmethod
    def _normalize(text: str) -> str:
        # Only ASCII punctuation goes, so emoji replies survive.
        decomposed = unicodedata.normalize('NFKD', text.lower())
        unaccented = ''.join(
            char
            for char in decomposed
            if not unicodedata.combining(char) and char not in EMOJI_MODIFIERS
        )
        words = unaccented.translate(str.maketrans('', '', string.punctuation)).split()
        return ' '.join(words)
