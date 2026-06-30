from bot.domain.commands.base import CommandScope
from bot.domain.commands.fuck import FuckCommand
from bot.domain.commands.hentai import HentaiCommand
from bot.domain.commands.porno import PornoCommand
from bot.domain.commands.rule34 import Rule34Command


def nsfw_commands():
    return [
        PornoCommand(),
        HentaiCommand(nhentai_mirror_url='https://example.test'),
        Rule34Command(),
        FuckCommand(),
    ]


class TestNsfwClassification:
    def test_plus18_commands_are_nsfw_scoped(self):
        scopes = {command.config.name: command.config.scope for command in nsfw_commands()}

        assert set(scopes.values()) == {CommandScope.NSFW}
