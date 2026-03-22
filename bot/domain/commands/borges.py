from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.mongodb import MongoDBConnection


class BorgesCommand(Command):
    COLLECTION_NAME = 'borges'
    COUNTER_ID = 'counter'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='borges', category='outras')

    @property
    def menu_description(self) -> str:
        return 'Descubra quantos nargas o Borges já fumou.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        collection = MongoDBConnection.collection(self.COLLECTION_NAME)
        result = await collection.find_one_and_update(
            {'_id': self.COUNTER_ID},
            {'$inc': {'nargas': 1}},
            return_document=True,
            upsert=True,
        )
        return [Reply.to(data).text(f'Borges já fumou {result["nargas"]} nargas 🚬')]
