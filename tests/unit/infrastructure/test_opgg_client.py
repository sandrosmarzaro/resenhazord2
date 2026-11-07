import json

import httpx
import pytest

from bot.infrastructure.opgg_client import OpggClient

MCP_URL = 'https://mcp-api.op.gg/mcp'

CUSTOM_FORMAT = """class Champion: summary, runes
class Summary: id, roles
class Runes: id, win
Champion(Summary(1, ['mid']), Runes(8112, 0.52))"""


def _answer(request: httpx.Request) -> httpx.Response:
    if json.loads(request.content)['method'] == 'initialize':
        return httpx.Response(200, json={'result': {'protocolVersion': '1.0.0'}})
    content = [{'type': 'text', 'text': CUSTOM_FORMAT}]
    return httpx.Response(200, json={'result': {'content': content}})


class TestCustomFormat:
    @pytest.mark.anyio
    async def test_parses_nested_classes_into_named_fields(self, respx_mock):
        respx_mock.post(MCP_URL).mock(side_effect=_answer)

        analysis = await OpggClient().get_champion_analysis('Ahri')

        assert analysis == {
            'champion': {
                'summary': {'id': 1, 'roles': ['mid']},
                'runes': {'id': 8112, 'win': 0.52},
            }
        }
