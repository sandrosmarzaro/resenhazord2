from typing import ClassVar

import httpx
import pytest
from structlog.testing import capture_logs

from bot.domain.services.translator import Translator


class TestToPt:
    DICTIONARY_URL = 'https://translate.googleapis.com/translate_a/t'
    WEB_URL = 'https://translate.googleapis.com/translate_a/single'
    WEB_TRANSLATION: ClassVar[list] = [
        [['Hoje é um ótimo dia.', 'Today is a great day.']],
    ]

    @pytest.mark.anyio
    async def test_translates_english_to_portuguese(self, respx_mock):
        respx_mock.get(url__startswith=self.DICTIONARY_URL).mock(
            return_value=httpx.Response(200, json=['Hoje é um ótimo dia.'])
        )

        result = await Translator.to_pt('Today is a great day.')

        assert result == 'Hoje é um ótimo dia.'

    @pytest.mark.anyio
    async def test_returns_original_when_both_clients_fail(self, respx_mock):
        respx_mock.get(url__startswith=self.DICTIONARY_URL).mock(return_value=httpx.Response(500))
        respx_mock.get(url__startswith=self.WEB_URL).mock(return_value=httpx.Response(429))

        result = await Translator.to_pt('Hello')

        assert result == 'Hello'

    @pytest.mark.anyio
    async def test_returns_original_on_empty_responses(self, respx_mock):
        respx_mock.get(url__startswith=self.DICTIONARY_URL).mock(
            return_value=httpx.Response(200, json=[])
        )
        respx_mock.get(url__startswith=self.WEB_URL).mock(return_value=httpx.Response(200, json=[]))

        result = await Translator.to_pt('Hello')

        assert result == 'Hello'

    @pytest.mark.anyio
    async def test_falls_back_to_the_web_client_when_blocked(self, respx_mock):
        respx_mock.get(url__startswith=self.DICTIONARY_URL).mock(return_value=httpx.Response(429))
        respx_mock.get(url__startswith=self.WEB_URL).mock(
            return_value=httpx.Response(200, json=self.WEB_TRANSLATION)
        )

        result = await Translator.to_pt('Today is a great day.')

        assert result == 'Hoje é um ótimo dia.'

    @pytest.mark.anyio
    async def test_logs_only_the_blocked_client(self, respx_mock):
        respx_mock.get(url__startswith=self.DICTIONARY_URL).mock(return_value=httpx.Response(429))
        respx_mock.get(url__startswith=self.WEB_URL).mock(
            return_value=httpx.Response(200, json=self.WEB_TRANSLATION)
        )

        with capture_logs() as logs:
            await Translator.to_pt('Hello')

        assert [log['upstream'] for log in logs if log['event'] == 'upstream_failed'] == [
            'google-dictionary'
        ]

    @pytest.mark.anyio
    async def test_joins_multiple_web_segments(self, respx_mock):
        multi_segment = [
            [['Primeira frase. ', 'First sentence. '], ['Segunda frase.', 'Second sentence.']],
        ]
        respx_mock.get(url__startswith=self.DICTIONARY_URL).mock(return_value=httpx.Response(429))
        respx_mock.get(url__startswith=self.WEB_URL).mock(
            return_value=httpx.Response(200, json=multi_segment)
        )

        result = await Translator.to_pt('First sentence. Second sentence.')

        assert result == 'Primeira frase. Segunda frase.'


class TestTranslate:
    DICTIONARY_URL = 'https://translate.googleapis.com/translate_a/t'
    WEB_URL = 'https://translate.googleapis.com/translate_a/single'

    @pytest.mark.anyio
    async def test_custom_language_pair(self, respx_mock):
        route = respx_mock.get(url__startswith=self.DICTIONARY_URL).mock(
            return_value=httpx.Response(200, json=['Hoy es un gran día.'])
        )

        result = await Translator.translate('Today is a great day.', source='en', target='es')

        assert result == 'Hoy es un gran día.'
        assert route.calls[0].request.url.params['tl'] == 'es'

    @pytest.mark.anyio
    async def test_fallback_keeps_the_language_pair(self, respx_mock):
        respx_mock.get(url__startswith=self.DICTIONARY_URL).mock(return_value=httpx.Response(429))
        route = respx_mock.get(url__startswith=self.WEB_URL).mock(
            return_value=httpx.Response(200, json=[[['Hoy es un gran día.', '']]])
        )

        await Translator.translate('Today is a great day.', source='en', target='es')

        assert route.calls[0].request.url.params['tl'] == 'es'
