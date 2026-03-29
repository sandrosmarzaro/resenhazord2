import struct

import httpx
import pytest

from bot.data.hentai_gallery import HentaiGallery
from bot.domain.commands.hentai import HentaiCommand
from bot.domain.models.message import ImageBufferContent
from bot.domain.services.hentai.hitomi_scraper import HitomiScraper
from bot.domain.services.hentai.nhentai_scraper import NhentaiScraper
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

MOCK_NHENTAI_RESPONSE = {
    'id': 999999,
    'media_id': '12345',
    'title': {
        'english': 'Test Nhentai Gallery',
        'japanese': 'テストNhentai',
        'pretty': 'Test Pretty',
    },
    'tags': [
        {'type': 'artist', 'name': 'nhartist'},
        {'type': 'group', 'name': 'nhgroup'},
        {'type': 'tag', 'name': 'nhtag1'},
        {'type': 'tag', 'name': 'nhtag2'},
        {'type': 'language', 'name': 'english'},
        {'type': 'category', 'name': 'manga'},
    ],
    'images': {
        'cover': {'t': 'j', 'w': 350, 'h': 500},
        'thumbnail': {'t': 'j', 'w': 250, 'h': 350},
        'pages': [],
    },
    'num_pages': 25,
    'upload_date': 1700000000,
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
    return respx_mock.get(url__startswith='https://nhentai.to/api/galleries/all')


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
        nhentai_route.mock(
            return_value=httpx.Response(200, json={'result': [MOCK_NHENTAI_RESPONSE]})
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_nhentai_caption_info(self, command, nhentai_route, nhentai_cover_route):
        data = GroupCommandDataFactory.build(text=',hentai nhentai')
        nhentai_route.mock(
            return_value=httpx.Response(200, json={'result': [MOCK_NHENTAI_RESPONSE]})
        )

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

        from bot.domain.exceptions import ExternalServiceError

        with pytest.raises(ExternalServiceError):
            await command.run(data)

    @pytest.mark.anyio
    async def test_nhentai_cover_url_format(self):
        scraper = NhentaiScraper()
        gallery = scraper._parse(MOCK_NHENTAI_RESPONSE)

        assert gallery.cover_url == 'https://t.nhentai.net/galleries/12345/thumb.jpg'

    @pytest.mark.anyio
    async def test_nhentai_date_formatting(self):
        scraper = NhentaiScraper()
        gallery = scraper._parse(MOCK_NHENTAI_RESPONSE)

        assert gallery.date == '2023-11'


class TestDefaultFallback:
    @pytest.mark.anyio
    async def test_falls_back_to_nhentai_on_hitomi_error(
        self, command, nozomi_route, nhentai_route, nhentai_cover_route
    ):
        data = GroupCommandDataFactory.build(text=',hentai')
        nozomi_route.mock(return_value=httpx.Response(200, content=b''))
        nhentai_route.mock(
            return_value=httpx.Response(200, json={'result': [MOCK_NHENTAI_RESPONSE]})
        )

        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)


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


class TestNhentaiExtMap:
    @pytest.mark.parametrize(
        ('ext_code', 'expected'),
        [
            ('j', 'jpg'),
            ('p', 'png'),
            ('g', 'gif'),
            ('w', 'webp'),
        ],
    )
    def test_ext_map(self, ext_code, expected):
        assert NhentaiScraper.EXT_MAP[ext_code] == expected

    def test_unknown_ext_defaults_to_jpg(self):
        assert NhentaiScraper.EXT_MAP.get('x', 'jpg') == 'jpg'
