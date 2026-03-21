import httpx
import pytest

from bot.domain.commands.puppy import PuppyCommand
from bot.domain.models.message import ImageBufferContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory

DOG_API_URL = 'https://dog.ceo/api/breeds/image/random'
CAT_API_URL = 'https://cataas.com/cat?json=true'


@pytest.fixture
def command():
    return PuppyCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', puppy', True),
            (',puppy', True),
            (', PUPPY', True),
            (', puppy dog', True),
            (', puppy cat', True),
            (', puppy show', True),
            (', puppy dm', True),
            ('  , puppy  ', True),
            ('puppy', False),
            ('hello', False),
            (', puppy extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestExtractBreed:
    def test_extracts_breed_from_url(self):
        url = 'https://images.dog.ceo/breeds/labrador/img.jpg'
        assert PuppyCommand._extract_breed(url) == 'Labrador'

    def test_extracts_multi_word_breed(self):
        url = 'https://images.dog.ceo/breeds/australian-shepherd/img.jpg'
        assert PuppyCommand._extract_breed(url) == 'Australian Shepherd'

    def test_returns_dog_when_no_match(self):
        url = 'https://example.com/random.jpg'
        assert PuppyCommand._extract_breed(url) == 'Dog'


class TestRun:
    @pytest.mark.anyio
    async def test_fetches_dog_with_option(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', puppy dog')
        route = respx_mock.get(DOG_API_URL).mock(
            return_value=httpx.Response(
                200, json={'message': 'https://images.dog.ceo/breeds/labrador/img.jpg'}
            )
        )
        respx_mock.get(url__startswith='https://images.dog.ceo/').mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        messages = await command.run(data)

        assert route.called
        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)
        assert messages[0].content.caption is not None
        assert 'Labrador' in messages[0].content.caption

    @pytest.mark.anyio
    async def test_fetches_cat_with_option(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', puppy cat')
        route = respx_mock.get(CAT_API_URL).mock(
            return_value=httpx.Response(200, json={'url': 'https://cataas.com/cat/abc'})
        )
        respx_mock.get(url__startswith='https://cataas.com/cat/').mock(
            return_value=httpx.Response(200, content=b'fake-cat')
        )
        messages = await command.run(data)

        assert route.called
        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)
        assert messages[0].content.caption is not None
        assert 'Cat' in messages[0].content.caption

    @pytest.mark.anyio
    async def test_random_choice_when_no_option(self, command, respx_mock, mocker):
        data = GroupCommandDataFactory.build(text=', puppy')
        respx_mock.get(DOG_API_URL).mock(
            return_value=httpx.Response(
                200, json={'message': 'https://images.dog.ceo/breeds/poodle/img.jpg'}
            )
        )
        respx_mock.get(url__startswith='https://images.dog.ceo/').mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        mocker.patch('bot.domain.commands.puppy.random.choice', return_value='dog')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_returns_error_text_on_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', puppy dog')
        respx_mock.get(DOG_API_URL).mock(side_effect=httpx.ConnectError('API down'))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text
