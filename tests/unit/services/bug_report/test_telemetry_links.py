import json
from urllib.parse import parse_qs, urlsplit

from bot.domain.services.bug_report.telemetry_links import TelemetryLinks

TRACE = '0af7651916cd43dd8448eb211c80319c'


def _pane(url: str) -> dict:
    return json.loads(parse_qs(urlsplit(url).query)['left'][0])


class TestGrafana:
    def test_tempo_opens_the_trace(self):
        links = TelemetryLinks(grafana_url='https://stack.grafana.net/')

        pane = _pane(links.tempo(TRACE))

        assert (pane['datasource'], pane['queries'][0]['query']) == ('grafanacloud-traces', TRACE)

    def test_loki_filters_the_logs_by_trace(self):
        links = TelemetryLinks(grafana_url='https://stack.grafana.net')

        pane = _pane(links.loki(TRACE))

        assert pane['queries'][0]['expr'] == f'{{service_name=~".+"}} | trace_id="{TRACE}"'

    def test_the_links_open_the_configured_stack(self):
        links = TelemetryLinks(grafana_url='https://stack.grafana.net/')

        assert links.tempo(TRACE).startswith('https://stack.grafana.net/explore?')

    def test_without_grafana_there_are_no_links(self):
        assert (TelemetryLinks().tempo(TRACE), TelemetryLinks().loki(TRACE)) == (None, None)


class TestSentry:
    def test_searches_the_correlation_id_tag(self):
        url = TelemetryLinks(sentry_org='acme').sentry('corr-1')

        assert url == 'https://acme.sentry.io/issues/?query=correlation_id%3Acorr-1&statsPeriod=14d'

    def test_without_an_org_there_is_no_link(self):
        assert TelemetryLinks().sentry('corr-1') is None
