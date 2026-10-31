"""List the agent proposals users denied, ready to paste into the eval.

    uv run task agent:denials             # the last 14 days (Loki's retention)
    uv run task agent:denials -- --days 3

Reads the agent_denied events from Loki through the Grafana instance (a service
account token with Viewer role). Each line is a DENIED_CASES entry for
tests/eval/dataset.py. Label the command the user wanted, and the case also
becomes a PROMPT_REGRESSION_CASES entry and a hand example in
bot/data/agent_examples.py (then `uv run task index:examples`).
"""

import argparse
import json
import time
from collections import Counter

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOKI_PATH = '/api/datasources/proxy/uid/grafanacloud-logs/loki/api/v1/query_range'
_QUERY = '{service_name="bot"} |= "agent_denied"'
_NANOS_PER_DAY = 86_400 * 10**9
_LIMIT = 5000
_TIMEOUT_SECONDS = 60
_MISSING = 'GRAFANA_URL and GRAFANA_TOKEN must be set to read the denials from Loki'


class GrafanaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    grafana_url: str = ''
    grafana_token: str = ''


def list_denials(settings: GrafanaSettings, days: int) -> str:
    end = time.time_ns()
    response = httpx.get(
        f'{settings.grafana_url.rstrip("/")}{_LOKI_PATH}',
        params={
            'query': _QUERY,
            'start': end - days * _NANOS_PER_DAY,
            'end': end,
            'limit': _LIMIT,
        },
        headers={'Authorization': f'Bearer {settings.grafana_token}'},
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    denials = Counter(
        (event['request'], event['proposed'])
        for stream in response.json()['data']['result']
        for _, line in stream['values']
        if (event := json.loads(line)).get('event') == 'agent_denied'
    )
    return '\n'.join(
        f'    ({request!r}, {proposed!r}),  # denied {count}x'
        for (request, proposed), count in denials.most_common()
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=14, help='how far back to look')
    arguments = parser.parse_args()

    configured = GrafanaSettings()
    if not configured.grafana_url or not configured.grafana_token:
        raise SystemExit(_MISSING)
    print(list_denials(configured, arguments.days) or 'No denials in this window.')
