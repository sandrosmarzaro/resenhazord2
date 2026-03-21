import pytest

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.menu import MenuCommand
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


@pytest.fixture
def command():
    return MenuCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',menu', True),
            (', menu', True),
            (', MENU', True),
            (', menu grupo', True),
            (', menu bíblia', True),
            (', menu biblia', True),
            ('menu', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestSectionMenus:
    @pytest.mark.anyio
    async def test_grupo_section(self, command):
        data = GroupCommandDataFactory.build(text=',menu grupo')
        messages = await command.run(data)

        assert len(messages) == 1
        text = messages[0].content.text
        assert 'COMANDOS DE GRUPO' in text
        assert ',grupo create' in text
        assert ',grupo delete' in text

    @pytest.mark.anyio
    async def test_biblia_section(self, command):
        data = GroupCommandDataFactory.build(text=',menu biblia')
        messages = await command.run(data)

        assert len(messages) == 1
        text = messages[0].content.text
        assert 'COMANDOS DE BÍBLIA' in text
        assert ',biblia' in text
        assert 'nvi' in text


class TestDynamicMenu:
    @pytest.mark.anyio
    async def test_builds_dynamic_menu(self, command):
        registry = CommandRegistry.instance()
        registry.register(command)

        data = GroupCommandDataFactory.build(text=',menu')
        messages = await command.run(data)

        assert len(messages) == 1
        text = messages[0].content.text
        assert 'MENU DE COMANDOS' in text
        assert 'OUTRAS FUNÇÕES' in text
        assert ',menu' in text
        assert 'Exibe o menu' in text

    @pytest.mark.anyio
    async def test_groups_by_category(self, command):
        from bot.domain.commands.d20 import D20Command
        from bot.domain.commands.oi import OiCommand

        registry = CommandRegistry.instance()
        registry.register(D20Command())
        registry.register(OiCommand())
        registry.register(command)

        data = GroupCommandDataFactory.build(text=',menu')
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'FUNÇÕES ALEATÓRIAS' in text
        assert ',d20' in text
        assert 'OUTRAS FUNÇÕES' in text
        assert ',oi' in text

    @pytest.mark.anyio
    async def test_aleatorias_has_subheader(self, command):
        from bot.domain.commands.d20 import D20Command

        registry = CommandRegistry.instance()
        registry.register(D20Command())
        registry.register(command)

        data = GroupCommandDataFactory.build(text=',menu')
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'show' in text
        assert 'dm' in text
        assert 'visualização única' in text

    @pytest.mark.anyio
    async def test_skips_commands_without_category(self, command):
        from unittest.mock import PropertyMock, patch

        from bot.domain.commands.base import CommandConfig
        from bot.domain.commands.d20 import D20Command

        d20 = D20Command()
        registry = CommandRegistry.instance()
        registry.register(d20)
        registry.register(command)

        no_category = CommandConfig(name='d20', category=None)
        with patch.object(type(d20), 'config', new_callable=PropertyMock, return_value=no_category):
            data = GroupCommandDataFactory.build(text=',menu')
            messages = await command.run(data)

        text = messages[0].content.text
        assert ',d20' not in text


class TestFormatOptions:
    @pytest.mark.anyio
    async def test_shows_command_aliases(self, command):
        from bot.domain.commands.my_anime_list import MyAnimeListCommand

        registry = CommandRegistry.instance()
        registry.register(MyAnimeListCommand())
        registry.register(command)

        data = GroupCommandDataFactory.build(text=',menu')
        messages = await command.run(data)

        text = messages[0].content.text
        assert ',anime* ou *,manga*' in text

    @pytest.mark.anyio
    async def test_shows_flags(self, command):
        from bot.domain.commands.fato import FatoCommand

        registry = CommandRegistry.instance()
        registry.register(FatoCommand())
        registry.register(command)

        data = GroupCommandDataFactory.build(text=',menu')
        messages = await command.run(data)

        text = messages[0].content.text
        assert '+hoje' in text

    @pytest.mark.anyio
    async def test_shows_required_args(self, command):
        from bot.domain.commands.download import DownloadCommand

        registry = CommandRegistry.instance()
        registry.register(DownloadCommand())
        registry.register(command)

        data = GroupCommandDataFactory.build(text=',menu')
        messages = await command.run(data)

        text = messages[0].content.text
        assert '<' in text  # required args use angle brackets

    @pytest.mark.anyio
    async def test_shows_optional_args(self, command):
        from bot.domain.commands.biblia import BibliaCommand

        registry = CommandRegistry.instance()
        token = 'test'  # noqa: S105
        registry.register(BibliaCommand(biblia_token=token))
        registry.register(command)

        data = GroupCommandDataFactory.build(text=',menu')
        messages = await command.run(data)

        text = messages[0].content.text
        assert '[' in text  # optional args use square brackets

    @pytest.mark.anyio
    async def test_shows_option_values(self, command):
        from bot.domain.commands.biblia import BibliaCommand

        registry = CommandRegistry.instance()
        token = 'test'  # noqa: S105
        registry.register(BibliaCommand(biblia_token=token))
        registry.register(command)

        data = GroupCommandDataFactory.build(text=',menu')
        messages = await command.run(data)

        text = messages[0].content.text
        assert '|' in text  # option values separated by pipe


class TestDmFlag:
    @pytest.mark.anyio
    async def test_dm_flag_changes_jid(self, command):
        data = GroupCommandDataFactory.build(
            text=',menu dm grupo',
            participant='5511999990000@s.whatsapp.net',
        )

        messages = await command.run(data)

        assert messages[0].jid == '5511999990000@s.whatsapp.net'


class TestPrivateChat:
    @pytest.mark.anyio
    async def test_works_in_private(self, command):
        data = PrivateCommandDataFactory.build(text=',menu')
        messages = await command.run(data)

        # MenuCommand has no group_only restriction
        assert len(messages) == 1
