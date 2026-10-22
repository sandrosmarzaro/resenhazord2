from bot.domain.models.conversation import Conversation, TurnIntent
from bot.domain.models.conversation_status import ConversationStatus

_NOW = 1000.0


def _confirming() -> Conversation:
    return Conversation().awaiting('Você quis dizer `,carro`?', _NOW, proposed_command=',carro')


class TestResumed:
    def test_keeps_a_question_inside_the_window(self):
        conversation = _confirming()

        resumed = conversation.resumed(_NOW + Conversation.RESUME_WINDOW_SECONDS)

        assert resumed == conversation

    def test_forgets_a_question_after_the_window(self):
        resumed = _confirming().resumed(_NOW + Conversation.RESUME_WINDOW_SECONDS + 1)

        assert resumed == Conversation()


class TestAwaiting:
    def test_a_proposed_command_awaits_confirmation_without_spending_an_attempt(self):
        conversation = _confirming()

        assert conversation.status == ConversationStatus.AWAITING_CONFIRMATION
        assert conversation.attempts == 0

    def test_a_question_awaits_an_answer_and_spends_an_attempt(self):
        conversation = Conversation().awaiting('Qual liga?', _NOW)

        assert conversation.status == ConversationStatus.AWAITING_ANSWER
        assert conversation.attempts == 1

    def test_two_questions_exhaust_the_attempts(self):
        conversation = Conversation().awaiting('Qual liga?', _NOW).awaiting('E o ano?', _NOW)

        assert conversation.exhausted


class TestIntent:
    def test_yes_confirms_a_pending_proposal(self):
        assert _confirming().intent('Sim!') == TurnIntent.CONFIRMED

    def test_no_denies_a_pending_proposal(self):
        assert _confirming().intent('não') == TurnIntent.DENIED

    def test_yes_without_a_proposal_is_a_request(self):
        assert Conversation().awaiting('Qual liga?', _NOW).intent('sim') == TurnIntent.REQUEST
