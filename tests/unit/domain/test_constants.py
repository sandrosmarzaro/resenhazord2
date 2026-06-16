from bot.domain.constants import (
    AGENT_MENU_HINT,
    CLARIFY_PREFIX,
    SUGGEST_PREFIX,
)


class TestConstants:
    def test_clarify_prefix(self):
        assert CLARIFY_PREFIX == ',clarify:'

    def test_suggest_prefix(self):
        assert SUGGEST_PREFIX == ',suggest:'

    def test_agent_menu_hint_is_nonempty(self):
        assert len(AGENT_MENU_HINT) > 0
