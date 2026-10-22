from enum import StrEnum


class ConversationStatus(StrEnum):
    IDLE = 'idle'
    AWAITING_CONFIRMATION = 'awaiting_confirmation'
    AWAITING_ANSWER = 'awaiting_answer'
