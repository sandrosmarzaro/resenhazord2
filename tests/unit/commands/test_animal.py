import httpx
import pytest

from bot.domain.commands.animal import AnimalCommand
from bot.domain.models.message import ImageBufferContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


@pytest.fixture
def command():
    return AnimalCommand()


@pytest.fixture
def wiki_route(respx_mock):
    return respx_mock.get(url__startswith='https://en.wikipedia.org/api/rest_v1/page/summary/')


@pytest.fixture
def image_route(respx_mock):
    return respx_mock.get(url__startswith='https://upload.wikimedia.org/').mock(
        return_value=httpx.Response(200, content=b'fake-image')
    )


@pytest.fixture
def translate_route(respx_mock):
    return respx_mock.get(
        url__startswith='https://translate.googleapis.com/translate_a/single'
    ).mock(return_value=httpx.Response(200, json=[[['Texto traduzido.', 'original']]]))


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',animal', True),
            (', animal', True),
            (', ANIMAL', True),
            (', animal show', True),
            (', animal dm', True),
            ('animal', False),
            ('hello', False),
            (', animal extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    MOCK_WIKIPEDIA_RESPONSE = {
        'extract': 'The giant panda is a bear species endemic to China. '
        'It is characterised by its black-and-white coat.',
        'thumbnail': {'source': 'https://upload.wikimedia.org/wikipedia/commons/thumb/panda.jpg'},
    }

    @pytest.mark.anyio
    async def test_returns_image_buffer(self, command, wiki_route, image_route, translate_route):
        data = GroupCommandDataFactory.build(text=',animal')
        wiki_route.mock(return_value=httpx.Response(200, json=self.MOCK_WIKIPEDIA_RESPONSE))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_caption_contains_emoji_name_fact(
        self, command, wiki_route, image_route, translate_route, mocker
    ):
        mocker.patch('bot.domain.commands.animal.random.choice', return_value='panda')
        translate_route.mock(
            return_value=httpx.Response(200, json=[[['urso gigante da China.', 'original']]])
        )
        data = GroupCommandDataFactory.build(text=',animal')
        wiki_route.mock(return_value=httpx.Response(200, json=self.MOCK_WIKIPEDIA_RESPONSE))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '🐼 Panda' in caption
        assert 'urso gigante da China.' in caption

    @pytest.mark.anyio
    async def test_formats_red_panda_name(
        self, command, wiki_route, image_route, translate_route, mocker
    ):
        mocker.patch('bot.domain.commands.animal.random.choice', return_value='red_panda')
        data = GroupCommandDataFactory.build(text=',animal')
        wiki_route.mock(return_value=httpx.Response(200, json=self.MOCK_WIKIPEDIA_RESPONSE))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'Red Panda' in caption

    @pytest.mark.anyio
    async def test_sends_user_agent_header(self, command, wiki_route, image_route, translate_route):
        data = GroupCommandDataFactory.build(text=',animal')
        wiki_route.mock(return_value=httpx.Response(200, json=self.MOCK_WIKIPEDIA_RESPONSE))
        await command.run(data)

        request = wiki_route.calls.last.request
        assert 'ResenhazordBot/2.0' in request.headers['user-agent']
        assert 'resenhazord2' in request.headers['user-agent']

    @pytest.mark.anyio
    async def test_text_only_when_no_thumbnail(self, command, wiki_route, translate_route):
        data = GroupCommandDataFactory.build(text=',animal')
        no_thumb = {**self.MOCK_WIKIPEDIA_RESPONSE, 'thumbnail': None}
        wiki_route.mock(return_value=httpx.Response(200, json=no_thumb))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)

    @pytest.mark.anyio
    async def test_extracts_first_two_sentences(
        self, command, wiki_route, image_route, translate_route
    ):
        data = GroupCommandDataFactory.build(text=',animal')
        wiki_data = {
            'extract': 'First sentence. Second sentence. Third sentence.',
            'thumbnail': {'source': 'https://upload.wikimedia.org/img.jpg'},
        }
        wiki_route.mock(return_value=httpx.Response(200, json=wiki_data))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_uses_first_sentence_when_two_exceed_300_chars(
        self, command, wiki_route, image_route, translate_route
    ):
        data = GroupCommandDataFactory.build(text=',animal')
        long_second = 'B' * 300
        wiki_data = {
            'extract': f'Short. {long_second}.',
            'thumbnail': {'source': 'https://upload.wikimedia.org/img.jpg'},
        }
        wiki_route.mock(return_value=httpx.Response(200, json=wiki_data))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)


class TestRateLimit:
    MOCK_WIKIPEDIA_RESPONSE = {
        'extract': 'The giant panda is a bear species endemic to China. '
        'It is characterised by its black-and-white coat.',
        'thumbnail': {'source': 'https://upload.wikimedia.org/wikipedia/commons/thumb/panda.jpg'},
    }

    @pytest.mark.anyio
    async def test_retries_on_429_with_retry_after(
        self, command, wiki_route, image_route, translate_route, mocker
    ):
        mocker.patch('bot.domain.commands.animal.anyio.sleep')
        data = GroupCommandDataFactory.build(text=',animal')
        wiki_route.mock(
            side_effect=[
                httpx.Response(429, headers={'retry-after': '60'}),
                httpx.Response(200, json=self.MOCK_WIKIPEDIA_RESPONSE),
            ]
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_defaults_to_60s_wait_when_no_retry_after(
        self, command, wiki_route, image_route, translate_route, mocker
    ):
        sleep_mock = mocker.patch('bot.domain.commands.animal.anyio.sleep')
        data = GroupCommandDataFactory.build(text=',animal')
        wiki_route.mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(200, json=self.MOCK_WIKIPEDIA_RESPONSE),
            ]
        )
        await command.run(data)

        sleep_mock.assert_called_with(60)

    @pytest.mark.anyio
    async def test_returns_empty_when_all_retries_rate_limited(self, command, wiki_route, mocker):
        mocker.patch('bot.domain.commands.animal.anyio.sleep')
        data = GroupCommandDataFactory.build(text=',animal')
        wiki_route.mock(return_value=httpx.Response(429, headers={'retry-after': '30'}))
        messages = await command.run(data)

        assert messages == []


class TestFlags:
    MOCK_WIKIPEDIA_RESPONSE = {
        'extract': 'The giant panda is a bear species endemic to China. '
        'It is characterised by its black-and-white coat.',
        'thumbnail': {'source': 'https://upload.wikimedia.org/wikipedia/commons/thumb/panda.jpg'},
    }

    @pytest.mark.anyio
    async def test_view_once_true_by_default(
        self, command, wiki_route, image_route, translate_route
    ):
        data = GroupCommandDataFactory.build(text=',animal')
        wiki_route.mock(return_value=httpx.Response(200, json=self.MOCK_WIKIPEDIA_RESPONSE))
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(
        self, command, wiki_route, image_route, translate_route
    ):
        data = GroupCommandDataFactory.build(text=',animal show')
        wiki_route.mock(return_value=httpx.Response(200, json=self.MOCK_WIKIPEDIA_RESPONSE))
        messages = await command.run(data)

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_dm_flag_redirects_jid(self, command, wiki_route, image_route, translate_route):
        data = GroupCommandDataFactory.build(text=',animal dm')
        wiki_route.mock(return_value=httpx.Response(200, json=self.MOCK_WIKIPEDIA_RESPONSE))
        messages = await command.run(data)

        assert messages[0].jid == data.participant

    @pytest.mark.anyio
    async def test_dm_flag_in_private_keeps_jid(
        self, command, wiki_route, image_route, translate_route
    ):
        data = PrivateCommandDataFactory.build(text=',animal dm')
        wiki_route.mock(return_value=httpx.Response(200, json=self.MOCK_WIKIPEDIA_RESPONSE))
        messages = await command.run(data)

        assert messages[0].jid == data.jid


class TestErrorHandling:
    @pytest.mark.anyio
    async def test_returns_error_text_on_api_failure(self, command, wiki_route):
        data = GroupCommandDataFactory.build(text=',animal')
        wiki_route.mock(side_effect=Exception('Network error'))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text
