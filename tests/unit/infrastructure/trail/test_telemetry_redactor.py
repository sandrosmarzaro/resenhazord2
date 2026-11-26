from bot.infrastructure.telemetry_redactor import TelemetryRedactor


class TestSecrets:
    def test_hides_a_telegram_bot_token_in_a_url(self):
        url = 'https://api.telegram.org/bot123456789:' 'AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw/getMe'

        assert TelemetryRedactor.text(url) == 'https://api.telegram.org/bot<redacted>/getMe'

    def test_hides_a_secret_query_parameter(self):
        url = 'https://api.example.com/v1?q=iene&api_key=abc123&page=2'

        assert (
            TelemetryRedactor.text(url)
            == 'https://api.example.com/v1?q=iene&api_key=<redacted>&page=2'
        )

    def test_query_keys_match_any_case(self):
        assert TelemetryRedactor.text('/x?Token=s3cr3t') == '/x?Token=<redacted>'

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
        assert TelemetryRedactor.value('/x?token=abc') == '/x?token=<redacted>'

    def test_an_object_is_shown_by_its_repr(self):
        assert TelemetryRedactor.value({'page': 2}) == "{'page': 2}"

    def test_bytes_show_only_their_size(self):
        assert TelemetryRedactor.value(b'\x00' * 5_000_000) == '<5000000 bytes>'

    def test_a_long_value_is_cut(self):
        assert len(TelemetryRedactor.value('a' * 10_000)) == TelemetryRedactor.MAX_CHARS
