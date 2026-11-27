import time

import pytest

from bot.infrastructure.telemetry_redactor import TelemetryRedactor

# Linear patterns take milliseconds here; a backtracking one takes seconds.
LINEAR_BUDGET_SECONDS = 0.5


class TestSecrets:
    def test_hides_a_telegram_bot_token_in_a_url(self):
        url = 'https://api.telegram.org/bot123456789:' + 'AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw/getMe'

        assert TelemetryRedactor.text(url) == 'https://api.telegram.org/bot<redacted>/getMe'

    def test_secret_names_match_any_case(self):
        assert TelemetryRedactor.text('Token=s3cr3t') == 'Token=<redacted>'

    def test_hides_the_password_in_a_connection_url(self):
        url = 'redis://default:hunter2@redis.example.com:12837'

        assert TelemetryRedactor.text(url) == 'redis://<redacted>@redis.example.com:12837'

    def test_hides_a_bearer_credential(self):
        assert TelemetryRedactor.text('Bearer eyJhbGciOiJIUzI1') == 'Bearer <redacted>'

    def test_hides_a_github_token(self):
        assert TelemetryRedactor.text('ghp_abcdefABCDEF1234') == '<redacted>'

    def test_keeps_plain_text(self):
        assert TelemetryRedactor.text('a cotação do iene veio errada') == (
            'a cotação do iene veio errada'
        )


class TestIdentities:
    def test_hashes_a_whatsapp_jid_in_text(self):
        jid = '5511999999999@s.whatsapp.net'

        redacted = TelemetryRedactor.text(f'mandei pra {jid}')

        assert redacted == f'mandei pra <id:{TelemetryRedactor.identity(jid)}>'

    def test_hashes_a_lid(self):
        assert '123456789012345' not in TelemetryRedactor.text('from 123456789012345@lid')

    def test_hashes_an_old_style_group_jid_whole(self):
        jid = '5511999999999-1600000000@g.us'

        assert TelemetryRedactor.text(jid) == f'<id:{TelemetryRedactor.identity(jid)}>'

    def test_hashes_a_bare_phone_number(self):
        assert '5511999999999' not in TelemetryRedactor.text(',add 5511999999999')

    def test_keeps_short_numbers(self):
        assert TelemetryRedactor.text(',d20 x3 took 1500 ms') == ',d20 x3 took 1500 ms'

    def test_the_same_identity_hashes_the_same(self):
        first = TelemetryRedactor.identity('5511999999999@s.whatsapp.net')

        assert first == TelemetryRedactor.identity('5511999999999@s.whatsapp.net')

    def test_different_identities_hash_apart(self):
        first = TelemetryRedactor.identity('5511999999999@s.whatsapp.net')

        assert first != TelemetryRedactor.identity('5511888888888@s.whatsapp.net')

    def test_the_hash_is_short(self):
        assert len(TelemetryRedactor.identity('5511999999999@s.whatsapp.net')) == 10


class TestValues:
    def test_a_string_is_redacted(self):
        assert TelemetryRedactor.value('/x?token=abc') == '/x?<redacted>'

    def test_an_object_is_shown_by_its_repr(self):
        assert TelemetryRedactor.value({'page': 2}) == "{'page': 2}"

    def test_bytes_show_only_their_size(self):
        assert TelemetryRedactor.value(b'\x00' * 5_000_000) == '<5000000 bytes>'

    def test_a_long_value_is_cut(self):
        assert len(TelemetryRedactor.value('a' * 10_000)) == TelemetryRedactor.MAX_CHARS


class TestUrlCredentials:
    def test_hides_username_only_userinfo(self):
        assert TelemetryRedactor.text('amqp://guest@edge:5672/') == 'amqp://<redacted>@edge:5672/'

    def test_hides_a_password_holding_an_at_sign(self):
        url = 'mongodb+srv://bot:p@ss:w0rd@cluster.example.net/db'

        assert TelemetryRedactor.text(url) == 'mongodb+srv://<redacted>@cluster.example.net/db'

    def test_drops_the_query_string_of_a_url(self):
        url = 'https://api.example.com/v1?q=iene&x_api_key=abc123'

        assert TelemetryRedactor.text(url) == 'https://api.example.com/v1?<redacted>'


class TestNamedSecrets:
    @pytest.mark.parametrize(
        'leak',
        [
            'x_api_key=abc123secret',
            'access_token=abc123secret',
            '"token": "abc123secret"',
            'client_secret: abc123secret',
            "{'password': 'abc123secret'}",
        ],
    )
    def test_hides_the_value_of_a_secret_name(self, leak):
        assert 'abc123secret' not in TelemetryRedactor.text(leak)


class TestProviderKeys:
    @pytest.mark.parametrize(
        'key',
        [
            'gsk_abcdefghijklmnop1234',
            'lsv2_pt_abcdefghijklmnop1234',
            'sk-abcdefghijklmnop1234',
            'xoxb-1234-abcdefghijklmnop',
            'AKIA' + 'ABCDEFGHIJKLMNOP',
            '123456789:' + 'AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw',
        ],
    )
    def test_hides_a_provider_key_in_free_text(self, key):
        assert key not in TelemetryRedactor.text(f'failed with {key} today')


class TestShortIdentities:
    @pytest.mark.parametrize(
        'jid', ['12345678@lid', '1234567@s.whatsapp.net', '123456@c.us', '1234567890@g.us']
    )
    def test_hashes_a_short_jid(self, jid):
        assert jid.split('@')[0] not in TelemetryRedactor.text(f'from {jid}')

    def test_hashes_a_phone_written_with_separators(self):
        assert '99999-9999' not in TelemetryRedactor.text('liga pra +55 (11) 99999-9999')

    def test_keeps_a_date(self):
        assert TelemetryRedactor.text('em 2026-11-26') == 'em 2026-11-26'


class TestRedactBeforeCut:
    def test_a_secret_past_the_cut_is_still_hidden(self):
        value = {'padding': 'a' * (TelemetryRedactor.MAX_CHARS - 20), 'api_key': 'abc123secret'}

        assert 'abc12' not in TelemetryRedactor.value(value)

    def test_a_long_string_with_a_secret_at_the_cut_is_hidden(self):
        value = 'a' * (TelemetryRedactor.MAX_CHARS - 10) + ' token=abc123secret'

        assert 'abc' not in TelemetryRedactor.value(value)


class TestLinearTime:
    @pytest.mark.parametrize(
        'adversarial',
        [
            'a' * 50_000,
            'a-' * 25_000,
            'key' * 20_000,
            'http' * 15_000,
            'http://' * 8_000,
            '1' * 50_000,
            '1-' * 25_000,
            '1' * 50_000 + '@',
        ],
        ids=['letters', 'dashes', 'names', 'schemes', 'urls', 'digits', 'digit-dashes', 'jid'],
    )
    def test_an_adversarial_input_finishes_fast(self, adversarial):
        started = time.perf_counter()

        TelemetryRedactor.text(adversarial)

        assert time.perf_counter() - started < LINEAR_BUDGET_SECONDS

    def test_a_deep_object_is_bounded_before_redaction(self):
        deep = [['x' * 10_000] * 10] * 10

        assert len(TelemetryRedactor.value(deep)) <= TelemetryRedactor.MAX_CHARS


class TestUserinfoPunctuation:
    @pytest.mark.parametrize('password', ['p?ss', 'p#ss', 'p?a#s@s'])
    def test_hides_a_password_with_url_punctuation(self, password):
        url = f'redis://default:{password}@redis.example.com:12837/0'

        assert TelemetryRedactor.text(url) == 'redis://<redacted>@redis.example.com:12837/0'

    def test_drops_a_fragment(self):
        url = 'https://app.example.com/callback#access_token=abc123'

        assert TelemetryRedactor.text(url) == 'https://app.example.com/callback#<redacted>'


class TestMoreSecretNames:
    @pytest.mark.parametrize(
        'leak',
        [
            'auth=abc123secret',
            'sig: abc123secret',
            'db_pwd=abc123secret',
            'pass: abc123secret',
            '"credential": "abc123secret"',
        ],
    )
    def test_hides_the_value_of_a_secret_name(self, leak):
        assert 'abc123secret' not in TelemetryRedactor.text(leak)

    def test_drops_a_scheme_less_query_string(self):
        assert (
            TelemetryRedactor.text('GET /v1/latest?q=iene&x=abc123') == 'GET /v1/latest?<redacted>'
        )


class TestPrefixedSecrets:
    def test_hides_a_telegram_token_after_a_colon(self):
        token = '123456789:' + 'AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw'

        assert token.split(':')[1] not in TelemetryRedactor.text(f'chat:{token}')

    @pytest.mark.parametrize('leak', ['x-sk-abcdefghijklmnop1234', 'api-gsk_abcdefghijklmnop1234'])
    def test_hides_a_provider_key_after_a_dash(self, leak):
        assert 'abcdefghijklmnop1234' not in TelemetryRedactor.text(f'with {leak}')


class TestElementRedactedBeforeItsCut:
    def test_a_secret_straddling_an_element_cut_is_hidden(self, mocker):
        mocker.patch.object(TelemetryRedactor, 'MAX_CHARS', 10_000)
        element = 'a' * 509 + ' token=' + 'b' * 600 + 'abc123secret'

        assert 'abc123secret' not in TelemetryRedactor.value([element])


class TestWholeCredentialAfterName:
    @pytest.mark.parametrize(
        ('leak', 'secret'),
        [
            ('authorization: Bot abc.def123', 'abc.def123'),
            ('authorization: Bearer xyz123', 'xyz123'),
            ('token="Bearer xyz123"', 'xyz123'),
            ("password='two secret words'", 'secret words'),
            ('token="unclosed xyz123', 'xyz123'),
            ('{"token": "Digest abc123"}', 'abc123'),
        ],
    )
    def test_hides_the_whole_value(self, leak, secret):
        assert secret not in TelemetryRedactor.text(leak)

    def test_a_quoted_value_keeps_its_quotes(self):
        assert TelemetryRedactor.text('token="a b"') == 'token="<redacted>"'


class TestSchemeCredentials:
    @pytest.mark.parametrize('scheme', ['Bot', 'Token', 'Bearer', 'Basic'])
    def test_hides_a_credential_after_its_scheme(self, scheme):
        assert 'abcd12345' not in TelemetryRedactor.text(f'sent with {scheme} abcd12345')

    def test_keeps_a_plain_word_after_bot(self):
        assert TelemetryRedactor.text('o bot respondeu errado') == 'o bot respondeu errado'


class TestDiscordBotToken:
    # Built at runtime so no scanner takes the test value for a real token.
    TOKEN = 'A' * 24 + '.' + 'B' * 6 + '.' + 'C' * 27

    def test_hides_a_discord_bot_token(self):
        assert self.TOKEN not in TelemetryRedactor.text(f'login failed for {self.TOKEN}')

    def test_a_long_dotted_run_finishes_fast(self):
        adversarial = ('A' * 24 + '.') * 2_000

        started = time.perf_counter()
        TelemetryRedactor.text(adversarial)

        assert time.perf_counter() - started < LINEAR_BUDGET_SECONDS


class TestDigitFreeSchemes:
    @pytest.mark.parametrize(
        'leak', ['Basic YWxhZGRpbjpvcGVuc2VzYW1l', 'Bearer abcdefghijklmnopqrstu']
    )
    def test_hides_a_credential_without_digits(self, leak):
        assert leak.split()[1] not in TelemetryRedactor.text(f'sent {leak} upstream')


class TestSecretInsideAQuotedValue:
    def test_hides_a_secret_inside_another_names_quoted_value(self):
        assert 'hunter2' not in TelemetryRedactor.text('msg="x password=hunter2"')

    def test_keeps_the_rest_of_that_value(self):
        assert TelemetryRedactor.text('msg="x password=hunter2"') == 'msg="x password=<redacted>"'
