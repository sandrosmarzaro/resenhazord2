import json
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import quote, urlencode


@dataclass(frozen=True)
class TelemetryLinks:
    """Links from a bug report into Grafana and Sentry. An unset base leaves them out.

    Tempo and Loki are opened by the OTel trace id. Sentry's own trace id is another
    one, so Sentry is searched by the correlation_id tag every command's events carry.
    """

    grafana_url: str = ''
    sentry_org: str = ''
    TRACES: ClassVar[str] = 'grafanacloud-traces'
    LOGS: ClassVar[str] = 'grafanacloud-logs'
    # Wider than the records' retention, so a report filed late still finds its data.
    RANGE: ClassVar[frozendict[str, str]] = frozendict({'from': 'now-7d', 'to': 'now'})
    SENTRY_PERIOD: ClassVar[str] = '14d'

    def tempo(self, trace_id: str) -> str | None:
        return self._explore(self.TRACES, {'queryType': 'traceql', 'query': trace_id})

    def loki(self, trace_id: str) -> str | None:
        return self._explore(self.LOGS, {'expr': f'{{service_name=~".+"}} | trace_id="{trace_id}"'})

    def sentry(self, correlation_id: str) -> str | None:
        if not self.sentry_org:
            return None
        query = urlencode(
            {'query': f'correlation_id:{correlation_id}', 'statsPeriod': self.SENTRY_PERIOD},
            quote_via=quote,
        )
        return f'https://{self.sentry_org}.sentry.io/issues/?{query}'

    def _explore(self, datasource: str, query: dict[str, str]) -> str | None:
        if not self.grafana_url:
            return None
        pane = {'datasource': datasource, 'queries': [{'refId': 'A', **query}], 'range': self.RANGE}
        left = json.dumps(pane, separators=(',', ':'), default=dict)
        return f'{self.grafana_url.rstrip("/")}/explore?{urlencode({"left": left})}'
