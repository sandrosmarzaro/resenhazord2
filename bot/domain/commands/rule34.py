from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    CommandScope,
    Flag,
    ParsedCommand,
    Platform,
)
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.rule34_images import Rule34Images


class Rule34Command(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='rule 34',
            aliases=['rule34', 'rule_34', 'r34'],
            flags=[Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            scope=CommandScope.NSFW,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Recebe uma imagem aleatória da Rule 34 (18+).'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        image = await Rule34Images.fetch()
        return [Reply.to(data).image(image, 'Aqui está a imagem que você pediu 🤗')]
