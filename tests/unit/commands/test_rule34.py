import httpx
import pytest
from structlog.testing import capture_logs

from bot.domain.commands.rule34 import Rule34Command
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.message import ImageContent
from tests.factories.command_data import GroupCommandDataFactory

RANDOM_PAGE_URL = 'https://rule34.xxx/index.php?page=post&s=random'
RULE34_IMAGE_URL = 'https://us.rule34.xxx//samples/1234/sample_abc.jpg?5678'
BANNER_URL = 'https://kanako.store/products/futa-body'
POSTS_URL = 'https://rule34.paheal.net/api/danbooru/find_posts'
POST_URL = 'https://r34i.paheal-cdn.net/aa/bb/kept'
SKIPPED_URL = 'https://r34i.paheal-cdn.net/aa/bb/skipped'


@pytest.fixture
def command():
    return Rule34Command()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', rule 34', True),
            (',rule 34', True),
            (', RULE 34', True),
            (', rule 34 show', True),
            (', rule 34 dm', True),
            ('  , rule 34  ', True),
            ('rule 34', False),
            ('hello', False),
            (', rule 34 extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


def _post(
    file_name: str = 'image.png', tags: str = 'tag_one tag_two tag_three', file_url: str = ''
) -> str:
    return (
        f"<post id='1' file_name='{file_name}' tags='{tags}' "
        f"file_url='{file_url or POST_URL}' rating='?'/>"
    )


def _posts(*posts: str) -> httpx.Response:
    return httpx.Response(200, text=f"<posts count='2' offset='0'>{''.join(posts)}</posts>")


def _page(
    alt: str = 'tag_one tag_two tag_three',
    sidebar: tuple[str, ...] = (),
    src: str = RULE34_IMAGE_URL,
) -> httpx.Response:
    links = ''.join(
        f'<li><a href="index.php?page=post&amp;s=list&amp;tags={tag}">{tag}</a></li>'
        for tag in sidebar
    )
    return httpx.Response(
        200,
        text=(
            f'<ul id="tag-sidebar">{links}</ul>'
            f'<div class="flexi"><img src="{BANNER_URL}"/><img src="{src}" alt="{alt}"/></div>'
        ),
    )


@pytest.fixture
def page_route(respx_mock):
    return respx_mock.get(RANDOM_PAGE_URL)


@pytest.fixture
def posts_route(respx_mock):
    return respx_mock.get(url__startswith=POSTS_URL).mock(return_value=_posts(_post()))


class TestRule34Source:
    @pytest.mark.anyio
    async def test_sends_the_image_of_the_random_page(self, command, page_route, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        page_route.mock(return_value=_page())

        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == RULE34_IMAGE_URL
        assert messages[0].content.caption == 'Aqui está a imagem que você pediu 🤗'
        assert not posts_route.called

    @pytest.mark.anyio
    async def test_reads_tags_from_the_sidebar(self, command, page_route, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        page_route.mock(return_value=_page(alt='', sidebar=('tag_one', 'tag_two', 'tag_three')))

        messages = await command.run(data)

        assert messages[0].content.url == RULE34_IMAGE_URL

    @pytest.mark.anyio
    async def test_captcha_falls_back_quietly(self, command, page_route, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        page_route.mock(return_value=httpx.Response(403))

        with capture_logs() as logs:
            messages = await command.run(data)

        assert messages[0].content.url == POST_URL
        assert [log['event'] for log in logs] == ['rule34_fallback']
        assert logs[0]['reason'] == 'captcha'

    @pytest.mark.anyio
    async def test_real_failure_falls_back_and_is_reported(self, command, page_route, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        page_route.mock(return_value=httpx.Response(500))

        with capture_logs() as logs:
            messages = await command.run(data)

        assert messages[0].content.url == POST_URL
        assert [(log['event'], log['upstream']) for log in logs] == [('upstream_failed', 'rule34')]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'page',
        [
            _page(alt='loli tag_two tag_three'),
            _page(alt='tag_one tag_two', sidebar=('shota',)),
            _page(alt='Child tag_two tag_three'),
        ],
        ids=['minor_alt', 'minor_sidebar', 'uppercase'],
    )
    async def test_a_post_tagged_as_a_minor_goes_to_the_fallback(
        self, command, page_route, posts_route, page
    ):
        data = GroupCommandDataFactory.build(text=',rule 34')
        page_route.mock(return_value=page)

        with capture_logs() as logs:
            messages = await command.run(data)

        assert messages[0].content.url == POST_URL
        assert logs[0]['reason'] == 'minor_tags'

    @pytest.mark.anyio
    @pytest.mark.parametrize('alt', ['tagme', 'tag_one tag_two'], ids=['tagme', 'few_tags'])
    async def test_a_barely_tagged_post_is_still_sent(self, command, page_route, posts_route, alt):
        data = GroupCommandDataFactory.build(text=',rule 34')
        page_route.mock(return_value=_page(alt=alt))

        with capture_logs() as logs:
            messages = await command.run(data)

        assert messages[0].content.url == RULE34_IMAGE_URL
        assert logs == []
        assert not posts_route.called

    @pytest.mark.anyio
    async def test_a_post_without_tags_is_sent_and_logged(self, command, page_route, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        page_route.mock(return_value=_page(alt=''))

        with capture_logs() as logs:
            messages = await command.run(data)

        assert messages[0].content.url == RULE34_IMAGE_URL
        assert [log['event'] for log in logs] == ['rule34_sent_without_tags']
        assert not posts_route.called

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'src',
        [
            'file:///etc/passwd',
            '/etc/passwd',
            'http://us.rule34.xxx/images/plain_http.jpg',
            'https://rule34.xxx.evil.example/image.jpg',
            'https://evil.example\\@us.rule34.xxx/image.jpg',
            'https://us.rule34.xxx/image with space.jpg',
        ],
    )
    async def test_only_sends_https_urls_from_its_cdn(self, command, page_route, posts_route, src):
        data = GroupCommandDataFactory.build(text=',rule 34')
        page_route.mock(return_value=_page(src=src))

        with capture_logs() as logs:
            messages = await command.run(data)

        assert messages[0].content.url == POST_URL
        assert logs[0]['reason'] == 'no_image'

    @pytest.mark.anyio
    async def test_a_page_without_an_image_goes_to_the_fallback(
        self, command, page_route, posts_route
    ):
        data = GroupCommandDataFactory.build(text=',rule 34')
        page_route.mock(return_value=httpx.Response(200, text='<div class="flexi"></div>'))

        with capture_logs() as logs:
            messages = await command.run(data)

        assert messages[0].content.url == POST_URL
        assert logs[0]['reason'] == 'no_image'


class TestPahealFallback:
    @pytest.fixture(autouse=True)
    def captcha(self, page_route):
        page_route.mock(return_value=httpx.Response(403))

    @pytest.mark.anyio
    async def test_returns_image(self, command, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        posts_route.mock(return_value=_posts(_post()))

        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == POST_URL
        assert messages[0].content.caption == 'Aqui está a imagem que você pediu 🤗'

    @pytest.mark.anyio
    async def test_asks_for_a_page_of_posts(self, command, posts_route, mocker):
        data = GroupCommandDataFactory.build(text=',rule 34')
        mocker.patch('bot.domain.services.rule34_images.random.randint', return_value=1234)
        posts_route.mock(return_value=_posts(_post()))

        await command.run(data)

        params = posts_route.calls[0].request.url.params
        assert params['page'] == '1234'
        assert params['limit'] == '25'

    @pytest.mark.anyio
    @pytest.mark.parametrize('file_name', ['clip.mp4', 'clip.webm', 'loop.gif', 'no_extension'])
    async def test_skips_what_is_not_an_image(self, command, posts_route, file_name):
        data = GroupCommandDataFactory.build(text=',rule 34')
        posts_route.mock(return_value=_posts(_post(file_name, file_url=SKIPPED_URL), _post()))

        messages = await command.run(data)

        assert messages[0].content.url == POST_URL

    @pytest.mark.anyio
    async def test_accepts_an_uppercase_extension(self, command, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        posts_route.mock(return_value=_posts(_post('IMAGE.JPEG')))

        messages = await command.run(data)

        assert messages[0].content.url == POST_URL

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'tags',
        [
            'loli tag_two tag_three',
            'Shotacon tag_two tag_three',
            'tag_one tag_two oppai_loli',
            'toddlercon',
        ],
    )
    async def test_never_picks_a_post_tagged_as_a_minor(self, command, posts_route, tags):
        data = GroupCommandDataFactory.build(text=',rule 34')
        posts_route.mock(return_value=_posts(_post(tags=tags, file_url=SKIPPED_URL), _post()))

        messages = await command.run(data)

        assert messages[0].content.url == POST_URL

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'file_url',
        [
            'file:///etc/passwd',
            '/etc/passwd',
            'http://r34i.paheal-cdn.net/aa/bb/plain_http',
            'https://evil.example/paheal-cdn.net',
            'https://paheal-cdn.net.evil.example/image',
            'https://evil.example\\@r34i.paheal-cdn.net/image',
            'https://user@r34i.paheal-cdn.net/image',
            'https://evil.example#.paheal-cdn.net/image',
            'https://r34i.paheal-cdn.net/aa/bb\\..\\image',
            'https://r34i.paheal-cdn.net/aa bb',
            'https://.paheal-cdn.net/image',
        ],
    )
    async def test_only_sends_https_urls_from_the_cdn(self, command, posts_route, file_url):
        data = GroupCommandDataFactory.build(text=',rule 34')
        posts_route.mock(return_value=_posts(_post(file_url=file_url), _post()))

        messages = await command.run(data)

        assert messages[0].content.url == POST_URL

    @pytest.mark.anyio
    async def test_checks_the_file_name_too(self, command, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        posts_route.mock(
            return_value=_posts(_post('loli_set_01.png', file_url=SKIPPED_URL), _post())
        )

        messages = await command.run(data)

        assert messages[0].content.url == POST_URL

    @pytest.mark.anyio
    async def test_reads_tags_with_an_escaped_apostrophe(self, command, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        posts_route.mock(return_value=_posts(_post(tags='Eddie&#039;s_mom tag_two tag_three')))

        messages = await command.run(data)

        assert messages[0].content.url == POST_URL

    @pytest.mark.anyio
    async def test_raises_when_no_post_qualifies(self, command, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        posts_route.mock(return_value=_posts(_post(tags='loli')))

        with pytest.raises(ExternalServiceError):
            await command.run(data)

    @pytest.mark.anyio
    async def test_raises_on_an_http_error(self, command, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        posts_route.mock(return_value=httpx.Response(500))

        with pytest.raises(httpx.HTTPStatusError):
            await command.run(data)

    @pytest.mark.anyio
    async def test_view_once_is_true(self, command, posts_route):
        data = GroupCommandDataFactory.build(text=',rule 34')
        posts_route.mock(return_value=_posts(_post()))

        messages = await command.run(data)

        assert messages[0].content.view_once is True
