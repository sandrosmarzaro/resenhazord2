import os

import pytest

from bot.infrastructure.llm.langchain_provider import LangChainProvider

MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

pytestmark = [
    pytest.mark.external,
    pytest.mark.skipif(not GROQ_API_KEY, reason='GROQ_API_KEY absent'),
]

_MENU_TOOL = {
    'type': 'function',
    'function': {
        'name': 'menu',
        'description': 'Lista todos os comandos disponíveis do bot',
        'parameters': {'type': 'object', 'properties': {}},
    },
}


class TestComplete:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_maps_a_clear_request_to_the_menu_tool(self):
        provider = LangChainProvider.from_credentials(MISTRAL_API_KEY or '', GROQ_API_KEY or '')

        response = await provider.complete('me mostra a lista de comandos', [_MENU_TOOL])

        assert response.tool_call is not None
        assert response.tool_call['name'] == 'menu'
