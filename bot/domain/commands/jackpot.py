import random
from collections import Counter

from bot.data.jackpot import JACKPOT_MESSAGE, LOSS_MESSAGE, PARTIAL_WIN_MESSAGE, SLOT_SYMBOLS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class JackpotCommand(Command):
    MATCH_ALL = 3
    MATCH_PAIR = 2
    REEL_COUNT = 3

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='jackpot',
            aliases=['slot', 'caçaníqueis', 'tigrinho'],
            category='random',
        )

    @property
    def menu_description(self) -> str:
        return 'Jogue na máquina caça-níqueis de emojis.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        reels = random.choices(SLOT_SYMBOLS, k=self.REEL_COUNT)  # noqa: S311
        result = self._evaluate(reels)
        text = (
            f'🎰 *JACKPOT* 🎰\n'
            f'╔══════════╗\n'
            f'║ {reels[0]} │ {reels[1]} │ {reels[2]} ║\n'
            f'╚══════════╝\n'
            f'{result}'
        )
        return [Reply.to(data).text(text)]

    @classmethod
    def _evaluate(cls, reels: list[str]) -> str:
        most_common = Counter(reels).most_common(1)[0][1]
        if most_common == cls.MATCH_ALL:
            return JACKPOT_MESSAGE
        if most_common == cls.MATCH_PAIR:
            return PARTIAL_WIN_MESSAGE
        return LOSS_MESSAGE
