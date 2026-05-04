from bot.domain.constants import (
    AGENT_MENU_HINT,
    CLARIFY_PREFIX,
    LLM_CLARIFY_MARKER,
    LLM_SUGGEST_MARKER,
    SUGGEST_PREFIX,
)


class TestConstants:
    def test_clarify_prefix(self):
        assert CLARIFY_PREFIX == ',clarify:'

    def test_suggest_prefix(self):
        assert SUGGEST_PREFIX == ',suggest:'

    def test_llm_clarify_marker(self):
        assert LLM_CLARIFY_MARKER == 'CLARIFY:'

    def test_llm_suggest_marker(self):
        assert LLM_SUGGEST_MARKER == 'SUGGEST:'

    def test_agent_menu_hint_is_nonempty(self):
        assert len(AGENT_MENU_HINT) > 0
