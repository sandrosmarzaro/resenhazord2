import json
from typing import ClassVar

from bot.data.browser_headers import BROWSER_HEADERS
from bot.infrastructure.http_client import HttpClient


class InstagramReels:
    # A logged-out visit to the Reels tab ships its first page of reels inside the HTML,
    # as the relay preload of PolarisLoggedOutDesktopWWWClipsContainerQuery. Reading it
    # needs no account, no lsd token and no doc_id, and each visit draws a fresh batch.
    FEED_URL: ClassVar[str] = 'https://www.instagram.com/reels/'
    # Without a navigation request the page comes back as an error shell or without
    # the preload.
    PAGE_HEADERS: ClassVar[dict[str, str]] = {**BROWSER_HEADERS, 'Sec-Fetch-Mode': 'navigate'}
    FEED_MARKER: ClassVar[str] = '"xig_logged_out_reels_feed":'
    REEL_URL: ClassVar[str] = 'https://www.instagram.com/reel/{code}/'

    @classmethod
    async def feed(cls) -> list[str]:
        page = await HttpClient.get(cls.FEED_URL, headers=cls.PAGE_HEADERS)
        page.raise_for_status()
        start = page.text.find(cls.FEED_MARKER)
        if start < 0:
            msg = 'Instagram Reels page opened no feed'
            raise RuntimeError(msg)

        feed, _ = json.JSONDecoder().raw_decode(page.text, start + len(cls.FEED_MARKER))
        if not feed['edges']:
            msg = 'Instagram Reels feed came back empty'
            raise RuntimeError(msg)
        return [cls.REEL_URL.format(code=edge['node']['code']) for edge in feed['edges']]
