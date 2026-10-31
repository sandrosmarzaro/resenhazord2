import json
import struct

import httpx
import pytest
from structlog.testing import capture_logs

from bot.data.hentai_gallery import HentaiGallery
from bot.domain.commands.hentai import HentaiCommand
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.message import ImageBufferContent
from bot.domain.services.hentai.hitomi_scraper import HitomiScraper
from tests.factories.command_data import GroupCommandDataFactory

MOCK_HITOMI_GALLERY_JS = (
    'var galleryinfo = '
    '{"id": "1234567",'
    '"title": "Test Gallery",'
    '"japanese_title": "テストギャラリー",'
    '"type": "doujinshi",'
    '"language": "japanese",'
    '"artists": [{"artist": "artist1"}],'
    '"groups": [{"group": "group1"}],'
    '"tags": [{"tag": "tag1"}, {"tag": "tag2"}],'
    '"files": [{"hash": "abcdef1234567890abcdef1234567890abcdef12", "name": "001.jpg",'
    '"width": 800, "height": 1200}],'
    '"date": "2024-01-15 12:00:00-05"}'
)

MOCK_NHENTAI_SEARCH = {'result': [{'id': 999999, 'media_id': '12345'}], 'num_pages': 1}

MOCK_NHENTAI_RESPONSE = {
    'id': 999999,
    'media_id': '12345',
    'title': {
        'english': 'Test Nhentai Gallery',
        'japanese': 'テストNhentai',
        'pretty': 'Test Pretty',
    },
    'cover': {'path': 'galleries/12345/cover.webp.webp', 'width': 350, 'height': 500},
    'tags': [
        {'type': 'artist', 'name': 'nhartist'},
        {'type': 'group', 'name': 'nhgroup'},
        {'type': 'tag', 'name': 'nhtag1'},
        {'type': 'tag', 'name': 'nhtag2'},
        {'type': 'language', 'name': 'translated'},
        {'type': 'language', 'name': 'english'},
        {'type': 'category', 'name': 'manga'},
    ],
    'num_pages': 25,
    'upload_date': 1700000000,
}

MOCK_EHENTAI_LISTING = """
<a href="https://e-hentai.org/g/4294761/0123456789/">a gallery</a>
<a href="https://e-hentai.org/g/4294761/0123456789/">the same gallery</a>
"""

MOCK_EHENTAI_METADATA = {
    'gid': 4294761,
    'token': '0123456789',
    'title': 'Test &amp; EHentai Gallery',
    'title_jpn': 'テストEHentai',
    'category': 'Doujinshi',
    'thumb': 'https://ehgt.org/w/02/761/61852-9ta9u1lj.webp',
    'filecount': '69',
    'posted': '1700000000',
    'tags': [
        'language:translated',
        'language:english',
        'artist:ehartist',
        'group:ehgroup',
        'parody:not a tag',
        'female:ehtag1',
        'male:ehtag2',
        'mixed:ehtag3',
        'other:ehtag4',
    ],
}


def _build_nozomi_data(*ids: int) -> bytes:
    return b''.join(struct.pack('>i', gid) for gid in ids)


@pytest.fixture
def command():
    return HentaiCommand()


@pytest.fixture
def nozomi_route(respx_mock):
    return respx_mock.get(
        url__startswith='https://ltn.gold-usergeneratedcontent.net/n/index-all.nozomi'
    )


@pytest.fixture
def gallery_js_route(respx_mock):
    return respx_mock.get(url__startswith='https://ltn.gold-usergeneratedcontent.net/galleries/')


@pytest.fixture
def hitomi_cover_route(respx_mock):
    return respx_mock.get(url__startswith='https://tn.gold-usergeneratedcontent.net/').mock(
        return_value=httpx.Response(200, content=b'fake-cover')
    )


@pytest.fixture
def nhentai_route(respx_mock):
    respx_mock.get(url__startswith='https://nhentai.net/api/v2/galleries/999999').mock(
        return_value=httpx.Response(200, json=MOCK_NHENTAI_RESPONSE)
    )
    return respx_mock.get(url__startswith='https://nhentai.net/api/v2/search')


@pytest.fixture
def ehentai_route(respx_mock):
    respx_mock.post('https://api.e-hentai.org/api.php').mock(
        return_value=httpx.Response(200, json={'gmetadata': [MOCK_EHENTAI_METADATA]})
    )
    return respx_mock.get(url__startswith='https://e-hentai.org/')


@pytest.fixture
def ehentai_cover_route(respx_mock):
    return respx_mock.get(url__startswith='https://ehgt.org/').mock(
        return_value=httpx.Response(200, content=b'fake-ehentai-cover')
    )


@pytest.fixture
def nhentai_cover_route(respx_mock):
    return respx_mock.get(url__startswith='https://t.nhentai.net/galleries/').mock(
        return_value=httpx.Response(200, content=b'fake-nhentai-cover')
    )


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',hentai', True),
            (', hentai', True),
            (', HENTAI', True),
            (', hentai ehentai', True),
            (', hentai hitomi', True),
            (', hentai nhentai', True),
            (', hentai dm', True),
            (', hentai show', True),
            ('hentai', False),
            ('hello', False),
            (', hentai extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestHitomi:
    @pytest.mark.anyio
    async def test_returns_image_buffer(
        self, command, nozomi_route, gallery_js_route, hitomi_cover_route
    ):
        data = GroupCommandDataFactory.build(text=',hentai hitomi')
        nozomi_route.mock(return_value=httpx.Response(206, content=_build_nozomi_data(1234567)))
        gallery_js_route.mock(return_value=httpx.Response(200, text=MOCK_HITOMI_GALLERY_JS))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_caption_contains_gallery_info(
        self, command, nozomi_route, gallery_js_route, hitomi_cover_route
    ):
        data = GroupCommandDataFactory.build(text=',hentai hitomi')
        nozomi_route.mock(return_value=httpx.Response(206, content=_build_nozomi_data(1234567)))
        gallery_js_route.mock(return_value=httpx.Response(200, text=MOCK_HITOMI_GALLERY_JS))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert 'Test Gallery' in caption
        assert 'テストギャラリー' in caption
        assert 'artist1' in caption
        assert 'group1' in caption
        assert 'doujinshi' in caption
        assert 'japanese' in caption
        assert 'tag1' in caption

    @pytest.mark.anyio
    async def test_cover_url_uses_thumbnail_format(self, nozomi_route, gallery_js_route):
        nozomi_route.mock(return_value=httpx.Response(206, content=_build_nozomi_data(1234567)))
        gallery_js_route.mock(return_value=httpx.Response(200, text=MOCK_HITOMI_GALLERY_JS))

        gallery = await HitomiScraper.fetch()
        file_hash = 'abcdef1234567890abcdef1234567890abcdef12'

        assert gallery.cover_url == (
            f'https://tn.gold-usergeneratedcontent.net/webpsmalltn/'
            f'{file_hash[-1]}/{file_hash[-3:-1]}/{file_hash}.webp'
        )

    @pytest.mark.anyio
    async def test_cover_headers_include_referer(self, nozomi_route, gallery_js_route):
        nozomi_route.mock(return_value=httpx.Response(206, content=_build_nozomi_data(1234567)))
        gallery_js_route.mock(return_value=httpx.Response(200, text=MOCK_HITOMI_GALLERY_JS))

        gallery = await HitomiScraper.fetch()

        assert gallery.cover_headers == {'Referer': 'https://hitomi.la/'}


class TestNhentai:
    @pytest.mark.anyio
    async def test_nhentai_flag_uses_nhentai(self, command, nhentai_route, nhentai_cover_route):
        data = GroupCommandDataFactory.build(text=',hentai nhentai')
        nhentai_route.mock(return_value=httpx.Response(200, json=MOCK_NHENTAI_SEARCH))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_nhentai_caption_info(self, command, nhentai_route, nhentai_cover_route):
        data = GroupCommandDataFactory.build(text=',hentai nhentai')
        nhentai_route.mock(return_value=httpx.Response(200, json=MOCK_NHENTAI_SEARCH))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert 'Test Nhentai Gallery' in caption
        assert 'nhartist' in caption
        assert 'nhgroup' in caption
        assert 'manga' in caption
        assert 'english' in caption

    @pytest.mark.anyio
    async def test_nhentai_raises_on_empty_listing(self, command, nhentai_route):
        data = GroupCommandDataFactory.build(text=',hentai nhentai')
        nhentai_route.mock(return_value=httpx.Response(200, json={'result': []}))

        with pytest.raises(ExternalServiceError):
            await command.run(data)

    @pytest.mark.anyio
    async def test_nhentai_falls_back_to_the_first_page(
        self, command, nhentai_route, nhentai_cover_route, mocker
    ):
        data = GroupCommandDataFactory.build(text=',hentai nhentai')
        mocker.patch('bot.domain.services.hentai.nhentai_scraper.random.randint', return_value=50)
        nhentai_route.mock(
            side_effect=[
                httpx.Response(200, json={'result': []}),
                httpx.Response(200, json=MOCK_NHENTAI_SEARCH),
            ]
        )

        messages = await command.run(data)

        assert nhentai_route.calls[-1].request.url.params['page'] == '1'
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_nhentai_search_excludes_minor_tags(
        self, command, nhentai_route, nhentai_cover_route
    ):
        data = GroupCommandDataFactory.build(text=',hentai nhentai')
        nhentai_route.mock(return_value=httpx.Response(200, json=MOCK_NHENTAI_SEARCH))

        await command.run(data)

        assert nhentai_route.calls[0].request.url.params['query'] == '-lolicon -shotacon'

    @pytest.mark.anyio
    async def test_nhentai_cover_comes_from_the_gallery_path(
        self, command, nhentai_route, nhentai_cover_route
    ):
        data = GroupCommandDataFactory.build(text=',hentai nhentai')
        nhentai_route.mock(return_value=httpx.Response(200, json=MOCK_NHENTAI_SEARCH))

        await command.run(data)

        assert str(nhentai_cover_route.calls[0].request.url) == (
            'https://t.nhentai.net/galleries/12345/cover.webp.webp'
        )

    @pytest.mark.anyio
    async def test_nhentai_caption_shows_month_language_and_link(
        self, command, nhentai_route, nhentai_cover_route
    ):
        data = GroupCommandDataFactory.build(text=',hentai nhentai')
        nhentai_route.mock(return_value=httpx.Response(200, json=MOCK_NHENTAI_SEARCH))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert '📅 2023-11' in caption
        assert '🌐 english' in caption
        assert 'https://nhentai.net/g/999999/' in caption


class TestEHentai:
    @pytest.mark.anyio
    async def test_flag_uses_ehentai(self, command, ehentai_route, ehentai_cover_route):
        data = GroupCommandDataFactory.build(text=',hentai ehentai')
        ehentai_route.mock(return_value=httpx.Response(200, text=MOCK_EHENTAI_LISTING))

        messages = await command.run(data)

        assert messages[0].content.data == b'fake-ehentai-cover'

    @pytest.mark.anyio
    async def test_caption_maps_the_metadata(self, command, ehentai_route, ehentai_cover_route):
        data = GroupCommandDataFactory.build(text=',hentai ehentai')
        ehentai_route.mock(return_value=httpx.Response(200, text=MOCK_EHENTAI_LISTING))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert '*Test & EHentai Gallery*' in caption
        assert 'テストEHentai' in caption
        assert '✍️ ehartist' in caption
        assert '👥 ehgroup' in caption
        assert '📚 doujinshi' in caption
        assert '🌐 english' in caption
        assert '🏷️ ehtag1, ehtag2, ehtag3, ehtag4' in caption
        assert '📄 69' in caption
        assert '📅 2023-11' in caption
        assert 'https://e-hentai.org/g/4294761/0123456789/' in caption

    @pytest.mark.anyio
    async def test_listing_asks_for_comics_without_minor_tags(
        self, command, ehentai_route, ehentai_cover_route
    ):
        data = GroupCommandDataFactory.build(text=',hentai ehentai')
        ehentai_route.mock(return_value=httpx.Response(200, text=MOCK_EHENTAI_LISTING))

        await command.run(data)

        params = ehentai_route.calls[0].request.url.params
        assert params['f_cats'] == '993'
        assert params['f_search'] == '-"female:lolicon$" -"male:shotacon$"'

    @pytest.mark.anyio
    async def test_gallery_requested_by_its_id_and_token(
        self, command, ehentai_route, ehentai_cover_route, respx_mock
    ):
        data = GroupCommandDataFactory.build(text=',hentai ehentai')
        ehentai_route.mock(return_value=httpx.Response(200, text=MOCK_EHENTAI_LISTING))

        await command.run(data)

        metadata_call = next(call for call in respx_mock.calls if call.request.method == 'POST')
        assert json.loads(metadata_call.request.content) == {
            'method': 'gdata',
            'gidlist': [[4294761, '0123456789']],
            'namespace': 1,
        }

    @pytest.mark.anyio
    async def test_empty_listing_raises(self, command, ehentai_route):
        data = GroupCommandDataFactory.build(text=',hentai ehentai')
        ehentai_route.mock(return_value=httpx.Response(200, text='Your IP address is banned'))

        with pytest.raises(ExternalServiceError):
            await command.run(data)

    @pytest.mark.anyio
    async def test_gallery_without_optional_metadata_gets_defaults(
        self, command, ehentai_route, ehentai_cover_route, respx_mock
    ):
        data = GroupCommandDataFactory.build(text=',hentai ehentai')
        ehentai_route.mock(return_value=httpx.Response(200, text=MOCK_EHENTAI_LISTING))
        bare = {**MOCK_EHENTAI_METADATA, 'title_jpn': '', 'tags': ['language:translated']}
        respx_mock.post('https://api.e-hentai.org/api.php').mock(
            return_value=httpx.Response(200, json={'gmetadata': [bare]})
        )

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert '🗾' not in caption
        assert '🌐 unknown' in caption


class TestDefaultFallback:
    @pytest.mark.anyio
    async def test_ehentai_is_the_default_source(self, command, ehentai_route, ehentai_cover_route):
        data = GroupCommandDataFactory.build(text=',hentai')
        ehentai_route.mock(return_value=httpx.Response(200, text=MOCK_EHENTAI_LISTING))

        messages = await command.run(data)

        assert messages[0].content.data == b'fake-ehentai-cover'

    @pytest.mark.anyio
    async def test_falls_back_to_hitomi_on_ehentai_error(
        self, command, ehentai_route, nozomi_route, gallery_js_route, hitomi_cover_route
    ):
        data = GroupCommandDataFactory.build(text=',hentai')
        ehentai_route.mock(return_value=httpx.Response(200, text=''))
        nozomi_route.mock(return_value=httpx.Response(206, content=_build_nozomi_data(1234567)))
        gallery_js_route.mock(return_value=httpx.Response(200, text=MOCK_HITOMI_GALLERY_JS))

        with capture_logs() as logs:
            messages = await command.run(data)

        assert messages[0].content.data == b'fake-cover'
        assert [log['upstream'] for log in logs if log['event'] == 'upstream_failed'] == ['ehentai']

    @pytest.mark.anyio
    async def test_falls_back_to_nhentai_when_the_others_fail(
        self, command, ehentai_route, nozomi_route, nhentai_route, nhentai_cover_route
    ):
        data = GroupCommandDataFactory.build(text=',hentai')
        ehentai_route.mock(return_value=httpx.Response(500))
        nozomi_route.mock(return_value=httpx.Response(200, content=b''))
        nhentai_route.mock(return_value=httpx.Response(200, json=MOCK_NHENTAI_SEARCH))

        with capture_logs() as logs:
            messages = await command.run(data)

        assert messages[0].content.data == b'fake-nhentai-cover'
        assert [log['upstream'] for log in logs if log['event'] == 'upstream_failed'] == [
            'ehentai',
            'hitomi',
        ]


class TestCoverRetry:
    @pytest.mark.anyio
    async def test_a_failed_cover_is_retried_and_logged(self, command, nhentai_route, respx_mock):
        data = GroupCommandDataFactory.build(text=',hentai nhentai')
        nhentai_route.mock(return_value=httpx.Response(200, json=MOCK_NHENTAI_SEARCH))
        respx_mock.get(url__startswith='https://t.nhentai.net/galleries/').mock(
            side_effect=[httpx.Response(404), httpx.Response(200, content=b'cover')]
        )

        with capture_logs() as logs:
            messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)
        assert [log['upstream'] for log in logs if log['event'] == 'upstream_failed'] == ['hentai']


class TestCaption:
    def test_caption_without_japanese_title(self):
        gallery = HentaiGallery(
            title='Test',
            japanese_title=None,
            artists=['a1'],
            groups=[],
            tags=['t1', 't2'],
            gallery_type='manga',
            language='english',
            pages=10,
            date='2024-01',
            cover_url='https://example.com/cover.jpg',
            url='https://example.com/g/1/',
        )
        caption = HentaiCommand._build_caption(gallery)

        assert '🗾' not in caption
        assert '📖 *Test*' in caption

    def test_caption_same_japanese_title_not_shown(self):
        gallery = HentaiGallery(
            title='Same Title',
            japanese_title='Same Title',
            artists=[],
            groups=[],
            tags=[],
            gallery_type='manga',
            language='english',
            pages=5,
            date='2024-01',
            cover_url='https://example.com/cover.jpg',
            url='https://example.com/g/1/',
        )
        caption = HentaiCommand._build_caption(gallery)

        assert '🗾' not in caption

    def test_caption_truncates_tags(self):
        many_tags = [f'tag{i}' for i in range(15)]
        gallery = HentaiGallery(
            title='Test',
            japanese_title=None,
            artists=[],
            groups=[],
            tags=many_tags,
            gallery_type='manga',
            language='english',
            pages=10,
            date='2024-01',
            cover_url='https://example.com/cover.jpg',
            url='https://example.com/g/1/',
        )
        caption = HentaiCommand._build_caption(gallery)

        assert '(+5 more)' in caption
        assert 'tag9' in caption
        assert 'tag10' not in caption

    def test_caption_no_artists_shows_dash(self):
        gallery = HentaiGallery(
            title='Test',
            japanese_title=None,
            artists=[],
            groups=[],
            tags=[],
            gallery_type='manga',
            language='english',
            pages=0,
            date='',
            cover_url='https://example.com/cover.jpg',
            url='https://example.com/g/1/',
        )
        caption = HentaiCommand._build_caption(gallery)

        assert '✍️ —' in caption
        assert '👥 —' in caption
        assert '🏷️ —' in caption


class TestNozomiParsing:
    def test_build_nozomi_data_packs_correctly(self):
        data = _build_nozomi_data(100, 200, 300)
        ids = [struct.unpack('>i', data[i * 4 : (i + 1) * 4])[0] for i in range(3)]
        assert ids == [100, 200, 300]


class TestThumbnailUrl:
    def test_builds_correct_thumbnail_url(self):
        file_hash = 'abcdef1234567890abcdef1234567890abcdef12'
        url = HitomiScraper._build_thumbnail_url(file_hash)

        assert url == (
            'https://tn.gold-usergeneratedcontent.net/webpsmalltn/2/f1/abcdef1234567890abcdef1234567890abcdef12.webp'
        )

    def test_thumbnail_url_extracts_hash_parts(self):
        file_hash = 'xyz123'
        url = HitomiScraper._build_thumbnail_url(file_hash)

        assert '/webpsmalltn/3/12/xyz123.webp' in url
