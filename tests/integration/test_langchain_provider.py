import os

import pytest

from bot.infrastructure.llm.langchain_provider import LangChainProvider

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

pytestmark = [
    pytest.mark.external,
    pytest.mark.skipif(not GITHUB_TOKEN, reason='GITHUB_TOKEN absent'),
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
        provider = LangChainProvider.from_credentials(
            GITHUB_TOKEN or '', MISTRAL_API_KEY or '', GROQ_API_KEY or ''
        )

        response = await provider.complete('me mostra a lista de comandos', [_MENU_TOOL])

        assert response.tool_call is not None
        assert response.tool_call['name'] == 'menu'
