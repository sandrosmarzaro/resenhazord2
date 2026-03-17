import pytest

from bot.domain.commands.puppy import PuppyCommand
from bot.domain.models.message import ImageBufferContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_json_response


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
    async def test_fetches_dog_with_option(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', puppy dog')
        dog_resp = make_json_response({'message': 'https://images.dog.ceo/breeds/labrador/img.jpg'})

        mock_get = mocker.patch('bot.domain.commands.puppy.HttpClient.get', return_value=dog_resp)
        mocker.patch(
            'bot.domain.commands.puppy.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        messages = await command.run(data)

        mock_get.assert_called_once_with('https://dog.ceo/api/breeds/image/random')
        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)
        assert 'Labrador' in messages[0].content.caption

    @pytest.mark.anyio
    async def test_fetches_cat_with_option(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', puppy cat')
        cat_resp = make_json_response({'url': 'https://cataas.com/cat/abc'})

        mock_get = mocker.patch('bot.domain.commands.puppy.HttpClient.get', return_value=cat_resp)
        mocker.patch(
            'bot.domain.commands.puppy.HttpClient.get_buffer',
            return_value=b'fake-cat',
        )
        messages = await command.run(data)

        mock_get.assert_called_once_with('https://cataas.com/cat?json=true')
        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)
        assert 'Cat' in messages[0].content.caption

    @pytest.mark.anyio
    async def test_random_choice_when_no_option(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', puppy')
        dog_resp = make_json_response({'message': 'https://images.dog.ceo/breeds/poodle/img.jpg'})

        mocker.patch('bot.domain.commands.puppy.HttpClient.get', return_value=dog_resp)
        mocker.patch(
            'bot.domain.commands.puppy.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        mocker.patch('bot.domain.commands.puppy.random.choice', return_value='dog')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_returns_error_text_on_failure(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', puppy dog')

        mocker.patch(
            'bot.domain.commands.puppy.HttpClient.get',
            side_effect=Exception('API down'),
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text
