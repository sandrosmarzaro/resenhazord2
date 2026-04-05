from typing import ClassVar

import httpx
import pytest

from bot.domain.services.translator import Translator


class TestToPt:
    URL = 'https://translate.googleapis.com/translate_a/single'
    MOCK_TRANSLATION: ClassVar[list] = [
        [['Hoje é um ótimo dia.', 'Today is a great day.']],
    ]

    @pytest.mark.anyio
    async def test_translates_english_to_portuguese(self, respx_mock):
        respx_mock.get(url__startswith=self.URL).mock(
            return_value=httpx.Response(200, json=self.MOCK_TRANSLATION)
        )

        result = await Translator.to_pt('Today is a great day.')

        assert result == 'Hoje é um ótimo dia.'

    @pytest.mark.anyio
    async def test_returns_original_on_http_error(self, respx_mock):
        respx_mock.get(url__startswith=self.URL).mock(return_value=httpx.Response(500))

        result = await Translator.to_pt('Hello')

        assert result == 'Hello'

    @pytest.mark.anyio
    async def test_returns_original_on_empty_response(self, respx_mock):
        respx_mock.get(url__startswith=self.URL).mock(return_value=httpx.Response(200, json=[]))

        result = await Translator.to_pt('Hello')

        assert result == 'Hello'

    @pytest.mark.anyio
    async def test_joins_multiple_segments(self, respx_mock):
        multi_segment = [
            [['Primeira frase. ', 'First sentence. '], ['Segunda frase.', 'Second sentence.']],
        ]
        respx_mock.get(url__startswith=self.URL).mock(
            return_value=httpx.Response(200, json=multi_segment)
        )

        result = await Translator.to_pt('First sentence. Second sentence.')

        assert result == 'Primeira frase. Segunda frase.'


class TestTranslate:
    URL = 'https://translate.googleapis.com/translate_a/single'

    @pytest.mark.anyio
    async def test_custom_language_pair(self, respx_mock):
        mock_es = [
            [['Hoy es un gran día.', 'Today is a great day.']],
        ]
        route = respx_mock.get(url__startswith=self.URL).mock(
            return_value=httpx.Response(200, json=mock_es)
        )

        result = await Translator.translate('Today is a great day.', source='en', target='es')

        assert result == 'Hoy es un gran día.'
        assert 'tl=es' in str(route.calls[0].request.url)
