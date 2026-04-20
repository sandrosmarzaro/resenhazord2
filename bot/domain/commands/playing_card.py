from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient


class PlayingCardCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='carta',
            aliases=['card'],
            flags=[Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            platforms=[Platform.WHATSAPP, Platform.DISCORD, Platform.TELEGRAM],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma carta de baralho aleatória.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        url = 'https://deckofcardsapi.com/api/deck/new/draw/?count=1'
        response = await HttpClient.get(url)
        response.raise_for_status()
        card = response.json()['cards'][0]
        return [Reply.to(data).image(card['image'], 'Era essa sua carta? 😏')]
