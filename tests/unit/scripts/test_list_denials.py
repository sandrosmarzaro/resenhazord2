import json

import httpx
import respx

from scripts.list_denials import GrafanaSettings, list_denials

_LOKI = (
    'https://stack.grafana.net/api/datasources/proxy/uid/grafanacloud-logs/loki/api/v1/query_range'
)


def _line(event: str, request: str = 'placar', proposed: str = ',placar now') -> list[str]:
    payload = {'event': event, 'request': request, 'proposed': proposed, 'reply': 'não'}
    return ['1793130000000000000', json.dumps(payload)]


def _loki(*lines: list[str]) -> httpx.Response:
    return httpx.Response(200, json={'data': {'result': [{'values': list(lines)}]}})


class TestListDenials:
    @respx.mock
    def test_counts_each_denied_mapping_most_frequent_first(self):
        respx.get(_LOKI).mock(
            return_value=_loki(
                _line('agent_denied', 'dado', ',d20'),
                _line('agent_denied'),
                _line('agent_denied'),
            )
        )
        settings = GrafanaSettings(grafana_url='https://stack.grafana.net/', grafana_token='t')

        listing = list_denials(settings, days=1)

        assert listing == (
            "    ('placar', ',placar now'),  # denied 2x\n    ('dado', ',d20'),  # denied 1x"
        )

    @respx.mock
    def test_skips_other_events_that_mention_a_denial(self):
        respx.get(_LOKI).mock(return_value=_loki(_line('agent_executing')))
        settings = GrafanaSettings(grafana_url='https://stack.grafana.net', grafana_token='t')

        assert list_denials(settings, days=1) == ''
