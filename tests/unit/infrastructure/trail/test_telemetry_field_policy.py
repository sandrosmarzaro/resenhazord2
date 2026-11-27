import pytest

from bot.infrastructure.telemetry_field_policy import TelemetryFieldPolicy
from bot.infrastructure.telemetry_redactor import TelemetryRedactor


class TestSecrets:
    @pytest.mark.parametrize('name', ['api_key', 'x-auth-token', 'db_pwd', 'client_secret'])
    def test_a_secret_name_hides_its_value(self, name):
        assert TelemetryFieldPolicy.show(name, 'abc123') == TelemetryRedactor.REDACTED

    def test_a_secret_name_wins_over_the_allowlist(self, mocker):
        mocker.patch(
            'bot.infrastructure.telemetry_field_policy.SAFE_FIELDS', frozenset({'status_token'})
        )

        assert TelemetryFieldPolicy.show('status_token', 'abc') == TelemetryRedactor.REDACTED


class TestIdentities:
    @pytest.mark.parametrize('name', ['chat', 'sender', 'channel_id', 'chat_jid', 'jid', 'user_id'])
    def test_an_identity_name_hashes_its_value(self, name):
        assert TelemetryFieldPolicy.show(name, -42) == TelemetryRedactor.identity('-42')


class TestAllowlist:
    def test_an_allowed_name_shows_its_value_redacted(self):
        assert TelemetryFieldPolicy.show('upstream', 'https://a.io/x?key=1') == (
            'https://a.io/x?<redacted>'
        )

    @pytest.mark.parametrize('name', ['text', 'message', 'quoted_text', 'currency', 'cache'])
    def test_any_other_name_is_dropped(self, name):
        assert TelemetryFieldPolicy.show(name, 'oi') is None


class TestUrls:
    def test_a_url_keeps_only_scheme_host_and_path(self):
        url = 'https://user:p@ss@api.example.com:8443/v1/latest?apikey=abc#top'

        assert (
            TelemetryFieldPolicy.show('http.url', url) == 'https://api.example.com:8443/v1/latest'
        )

    def test_a_url_path_token_is_redacted(self):
        url = 'https://api.telegram.org/bot123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw/getMe'

        assert TelemetryFieldPolicy.show('url.full', url) == (
            'https://api.telegram.org/bot<redacted>/getMe'
        )


class _Leaky:
    def __repr__(self) -> str:
        return '<Leaky 5511999999999@s.whatsapp.net token=abc123secret>'


class TestRichValues:
    def test_an_allowed_name_holding_an_object_shows_only_its_type(self):
        assert TelemetryFieldPolicy.show('status', _Leaky()) == '<_Leaky>'

    def test_an_allowed_name_holding_a_dict_shows_only_its_type(self):
        assert TelemetryFieldPolicy.show('status', {'chat': '5511999999999'}) == '<dict>'

    @pytest.mark.parametrize('value', [2, 1.5, True, None, 'ok'])
    def test_an_allowed_name_holding_a_plain_value_shows_it(self, value):
        assert TelemetryFieldPolicy.show('status', value) == TelemetryRedactor.value(value)
