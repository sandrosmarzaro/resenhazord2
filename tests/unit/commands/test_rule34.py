import httpx
import pytest

from bot.domain.commands.rule34 import Rule34Command
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.message import ImageContent
from tests.factories.command_data import GroupCommandDataFactory

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


class TestRun:
    @pytest.fixture
    def posts_route(self, respx_mock):
        return respx_mock.get(url__startswith=POSTS_URL)

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
        mocker.patch('bot.domain.commands.rule34.random.randint', return_value=1234)
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
