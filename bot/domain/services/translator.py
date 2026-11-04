from typing import ClassVar

import httpx
import structlog

from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class Translator:
    # Google blocks each client id per IP on its own. The gtx client gets the "unusual
    # traffic" 429 for hours on datacenter IPs, while the Chrome dictionary extension's
    # client still answers from the same IP, so it goes first.
    DICTIONARY_URL = 'https://translate.googleapis.com/translate_a/t'
    TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'
    _ERRORS: ClassVar[tuple[type[Exception], ...]] = (
        httpx.HTTPError,
        KeyError,
        IndexError,
        TypeError,
    )

    @classmethod
    async def to_pt(cls, text: str) -> str:
        return await cls.translate(text, source='en', target='pt')

    @classmethod
    async def translate(cls, text: str, *, source: str = 'en', target: str = 'pt') -> str:
        params = {'sl': source, 'tl': target, 'q': text}
        try:
            return await cls._translate_dictionary(params)
        except cls._ERRORS:
            logger.warning(
                'upstream_failed', upstream='google-dictionary', source=source, target=target
            )
        try:
            return await cls._translate_web(params)
        except cls._ERRORS:
            logger.warning(
                'upstream_failed', upstream='google-translate', source=source, target=target
            )
            return text

    @classmethod
    async def _translate_web(cls, params: dict[str, str]) -> str:
        response = await HttpClient.get(
            cls.TRANSLATE_URL, params={'client': 'gtx', 'dt': 't', **params}
        )
        response.raise_for_status()
        segments = response.json()[0]
        return ''.join(seg[0] for seg in segments if seg[0])

    @classmethod
    async def _translate_dictionary(cls, params: dict[str, str]) -> str:
        response = await HttpClient.get(
            cls.DICTIONARY_URL, params={'client': 'dict-chrome-ex', **params}
        )
        response.raise_for_status()
        return response.json()[0]
