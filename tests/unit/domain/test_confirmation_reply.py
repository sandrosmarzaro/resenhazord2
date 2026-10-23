import pytest

from bot.domain.models.confirmation_reply import ConfirmationReply


class TestClassify:
    @pytest.mark.parametrize(
        'text', ['sim', 'Sim!', 'SIM', ' s ', 'isso', 'pode ser', 'bora', '👍', '👍🏽', '✅\ufe0f']
    )
    def test_recognizes_yes(self, text):
        assert ConfirmationReply.classify(text) == ConfirmationReply.YES

    @pytest.mark.parametrize('text', ['não', 'Não.', 'nao', 'N', 'errado', '👎'])
    def test_recognizes_no(self, text):
        assert ConfirmationReply.classify(text) == ConfirmationReply.NO

    @pytest.mark.parametrize('text', ['me manda um carro', 'sim, mas de moto', '', 'simples'])
    def test_anything_else_is_other(self, text):
        assert ConfirmationReply.classify(text) == ConfirmationReply.OTHER
