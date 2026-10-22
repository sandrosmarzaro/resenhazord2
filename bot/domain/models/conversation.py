from dataclasses import dataclass, replace
from enum import StrEnum
from typing import ClassVar

from bot.domain.models.confirmation_reply import ConfirmationReply
from bot.domain.models.conversation_status import ConversationStatus


class TurnIntent(StrEnum):
    REQUEST = 'request'
    CONFIRMED = 'confirmed'
    DENIED = 'denied'


@dataclass(frozen=True)
class Conversation:
    """What the agent is waiting for in one chat, and for how long it keeps waiting."""

    RESUME_WINDOW_SECONDS: ClassVar[float] = 180.0
    MAX_ATTEMPTS: ClassVar[int] = 2

    status: ConversationStatus = ConversationStatus.IDLE
    question: str = ''
    proposed_command: str = ''
    attempts: int = 0
    asked_at: float = 0.0

    @property
    def exhausted(self) -> bool:
        return self.attempts >= self.MAX_ATTEMPTS

    def resumed(self, now: float) -> Conversation:
        if now - self.asked_at > self.RESUME_WINDOW_SECONDS:
            return Conversation()
        return self

    def awaiting(self, question: str, now: float, *, proposed_command: str = '') -> Conversation:
        # A proposal is answered by yes/no; only open questions spend an attempt.
        if proposed_command:
            return replace(
                self,
                status=ConversationStatus.AWAITING_CONFIRMATION,
                question=question,
                proposed_command=proposed_command,
                asked_at=now,
            )
        return replace(
            self,
            status=ConversationStatus.AWAITING_ANSWER,
            question=question,
            proposed_command='',
            attempts=self.attempts + 1,
            asked_at=now,
        )

    def intent(self, text: str) -> TurnIntent:
        if self.status != ConversationStatus.AWAITING_CONFIRMATION:
            return TurnIntent.REQUEST
        reply = ConfirmationReply.classify(text)
        if reply == ConfirmationReply.YES:
            return TurnIntent.CONFIRMED
        if reply == ConfirmationReply.NO:
            return TurnIntent.DENIED
        return TurnIntent.REQUEST
