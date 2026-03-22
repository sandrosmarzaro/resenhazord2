import httpx
import structlog

from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class Translator:
    TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'

    @classmethod
    async def to_pt(cls, text: str) -> str:
        return await cls.translate(text, source='en', target='pt')

    @classmethod
    async def translate(cls, text: str, *, source: str = 'en', target: str = 'pt') -> str:
        try:
            params = {
                'client': 'gtx',
                'sl': source,
                'tl': target,
                'dt': 't',
                'q': text,
            }
            response = await HttpClient.get(cls.TRANSLATE_URL, params=params)
            response.raise_for_status()
            segments = response.json()[0]
            return ''.join(seg[0] for seg in segments if seg[0])
        except (httpx.HTTPError, KeyError, IndexError, TypeError):
            logger.warning('translation_failed', source=source, target=target)
            return text
