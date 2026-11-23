import random

import httpx
import pytest

from bot.data.redgifs_media import RedGifsMedia
from bot.domain.exceptions import ExternalServiceError, MediaNotFoundError
from bot.domain.services.mp4_remux import Mp4Remux
from bot.domain.services.redgifs import RedGifs

AUTH_URL = 'https://api.redgifs.com/v2/auth/temporary'
SEARCH_URL = 'https://api.redgifs.com/v2/gifs/search'
VIDEO = 1
IMAGE = 2


def _item(name: str, kind: int = VIDEO, tags: list[str] | None = None) -> dict:
    return {
        'type': kind,
        'tags': tags or ['Feet'],
        'niches': [],
        'urls': {
            'sd': f'https://media.redgifs.com/{name}-mobile.mp4',
            'hd': f'https://media.redgifs.com/{name}.mp4',
        },
    }


def _page(*items: dict, pages: int = 1) -> httpx.Response:
    return httpx.Response(200, json={'gifs': list(items), 'pages': pages})


@pytest.fixture
def auth_route(respx_mock):
    return respx_mock.get(AUTH_URL).mock(
        return_value=httpx.Response(200, json={'token': 'temporary-token'})
    )


class TestRandomMedia:
    @pytest.mark.anyio
    async def test_returns_the_mobile_url_of_a_video(self, respx_mock, auth_route):
        respx_mock.get(url__startswith=SEARCH_URL).mock(return_value=_page(_item('Clip')))

        media = await RedGifs().random_media('Feet')

        assert media == RedGifsMedia(url='https://media.redgifs.com/Clip-mobile.mp4', is_video=True)

    @pytest.mark.anyio
    async def test_marks_an_image_as_not_a_video(self, respx_mock, auth_route):
        respx_mock.get(url__startswith=SEARCH_URL).mock(
            return_value=_page(_item('Photo', kind=IMAGE))
        )

        media = await RedGifs().random_media('Feet')

        assert media.is_video is False

    @pytest.mark.anyio
    async def test_searches_the_tag_with_the_temporary_token(self, respx_mock, auth_route):
        search = respx_mock.get(url__startswith=SEARCH_URL).mock(return_value=_page(_item('A')))

        await RedGifs().random_media('Redhead')

        request = search.calls[0].request
        assert request.url.params['tags'] == 'Redhead'
        assert request.headers['Authorization'] == 'Bearer temporary-token'

    @pytest.mark.anyio
    async def test_reuses_the_token_across_searches(self, respx_mock, auth_route):
        respx_mock.get(url__startswith=SEARCH_URL).mock(return_value=_page(_item('A')))
        redgifs = RedGifs()

        await redgifs.random_media('Feet')
        await redgifs.random_media('Feet')

        assert auth_route.call_count == 1

    @pytest.mark.anyio
    async def test_renews_an_expired_token(self, respx_mock, auth_route):
        respx_mock.get(url__startswith=SEARCH_URL).mock(
            side_effect=[httpx.Response(401), _page(_item('Clip'))]
        )

        media = await RedGifs().random_media('Feet')

        assert auth_route.call_count == 2
        assert media.url == 'https://media.redgifs.com/Clip-mobile.mp4'

    @pytest.mark.anyio
    async def test_asks_only_for_videos_when_told_to(self, respx_mock, auth_route):
        search = respx_mock.get(url__startswith=SEARCH_URL).mock(return_value=_page(_item('A')))

        await RedGifs().random_media('Sex', video_only=True)

        assert search.calls[0].request.url.params['type'] == 'g'


class TestPages:
    @pytest.mark.anyio
    async def test_starts_from_the_first_page(self, respx_mock, auth_route):
        search = respx_mock.get(url__startswith=SEARCH_URL).mock(return_value=_page(_item('A')))

        await RedGifs().random_media('Feet')

        assert search.calls[0].request.url.params['page'] == '1'

    @pytest.mark.anyio
    async def test_draws_the_page_within_the_pages_the_tag_has(
        self, respx_mock, auth_route, mocker
    ):
        respx_mock.get(url__startswith=SEARCH_URL).mock(return_value=_page(_item('A'), pages=3))
        draw = mocker.patch.object(random, 'randint', return_value=1)

        await RedGifs().random_media('Feet')

        draw.assert_called_once_with(1, 3)

    @pytest.mark.anyio
    async def test_caps_the_draw_at_the_trending_depth(self, respx_mock, auth_route, mocker):
        respx_mock.get(url__startswith=SEARCH_URL).mock(return_value=_page(_item('A'), pages=250))
        draw = mocker.patch.object(random, 'randint', return_value=1)

        await RedGifs().random_media('Feet')

        draw.assert_called_once_with(1, RedGifs.MAX_PAGE)

    @pytest.mark.anyio
    async def test_fetches_the_drawn_page(self, respx_mock, auth_route, mocker):
        search = respx_mock.get(url__startswith=SEARCH_URL).mock(
            side_effect=[_page(_item('First'), pages=3), _page(_item('Third'), pages=3)]
        )
        mocker.patch.object(random, 'randint', return_value=3)

        media = await RedGifs().random_media('Feet')

        assert search.calls[1].request.url.params['page'] == '3'
        assert media.url == 'https://media.redgifs.com/Third-mobile.mp4'

    @pytest.mark.anyio
    async def test_reuses_the_first_page_when_it_is_drawn(self, respx_mock, auth_route, mocker):
        search = respx_mock.get(url__startswith=SEARCH_URL).mock(
            return_value=_page(_item('A'), pages=3)
        )
        mocker.patch.object(random, 'randint', return_value=1)

        await RedGifs().random_media('Feet')

        assert search.call_count == 1

    @pytest.mark.anyio
    async def test_raises_not_found_when_the_tag_has_nothing(self, respx_mock, auth_route):
        respx_mock.get(url__startswith=SEARCH_URL).mock(return_value=_page(pages=0))
        redgifs = RedGifs()

        with pytest.raises(MediaNotFoundError):
            await redgifs.random_media('Xqzvwk')


class TestMinors:
    @pytest.mark.anyio
    async def test_skips_items_tagged_with_a_minor_term(self, respx_mock, auth_route):
        respx_mock.get(url__startswith=SEARCH_URL).mock(
            return_value=_page(_item('Unsafe', tags=['Feet', 'Teen']), _item('Safe'))
        )

        urls = {(await RedGifs().random_media('Feet')).url for _ in range(10)}

        assert urls == {'https://media.redgifs.com/Safe-mobile.mp4'}

    @pytest.mark.anyio
    async def test_skips_items_in_a_minor_niche(self, respx_mock, auth_route):
        unsafe = {**_item('Unsafe'), 'niches': ['teen-girls']}
        respx_mock.get(url__startswith=SEARCH_URL).mock(return_value=_page(unsafe, _item('Safe')))

        urls = {(await RedGifs().random_media('Feet')).url for _ in range(10)}

        assert urls == {'https://media.redgifs.com/Safe-mobile.mp4'}

    @pytest.mark.anyio
    async def test_raises_when_nothing_safe_is_left(self, respx_mock, auth_route):
        respx_mock.get(url__startswith=SEARCH_URL).mock(
            return_value=_page(_item('Unsafe', tags=['Petite', 'Teen']))
        )
        redgifs = RedGifs()

        with pytest.raises(ExternalServiceError):
            await redgifs.random_media('Feet')


class TestDownload:
    @pytest.mark.anyio
    async def test_remuxes_the_downloaded_video(self, respx_mock, mocker):
        respx_mock.get('https://media.redgifs.com/Clip-mobile.mp4').mock(
            return_value=httpx.Response(200, content=b'm4v-mp4')
        )
        remux = mocker.patch.object(Mp4Remux, 'remux', return_value=b'isom-mp4')

        video = await RedGifs.download('https://media.redgifs.com/Clip-mobile.mp4')

        assert video == b'isom-mp4'
        remux.assert_called_once_with(b'm4v-mp4')
