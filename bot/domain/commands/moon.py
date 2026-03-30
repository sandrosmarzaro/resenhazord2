import math
from datetime import UTC, datetime

from bot.data.moon import MOON_PHASES
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class MoonCommand(Command):
    SYNODIC_MONTH = 29.53058770576
    KNOWN_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=UTC)
    SECONDS_PER_DAY = 86400
    PHASE_COUNT = 8

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='lua',
            aliases=['moon'],
            category=Category.OTHER,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Mostra a fase atual da lua.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        now = datetime.now(tz=UTC)
        age = self._moon_age(now)
        phase = MOON_PHASES[self._phase_index(age)]
        illumination = self._illumination(age)
        date_str = now.strftime('%d/%m/%Y')
        text = f'{phase["emoji"]} *{phase["name"]}*\n📅 {date_str}\n🔭 Iluminação: ~{illumination}%'
        return [Reply.to(data).text(text)]

    @classmethod
    def _moon_age(cls, dt: datetime) -> float:
        diff = (dt - cls.KNOWN_NEW_MOON).total_seconds() / cls.SECONDS_PER_DAY
        return diff % cls.SYNODIC_MONTH

    @classmethod
    def _phase_index(cls, age: float) -> int:
        half_phase = cls.SYNODIC_MONTH / (cls.PHASE_COUNT * 2)
        return int((age + half_phase) / cls.SYNODIC_MONTH * cls.PHASE_COUNT) % cls.PHASE_COUNT

    @classmethod
    def _illumination(cls, age: float) -> int:
        return round(50 * (1 - math.cos(2 * math.pi * age / cls.SYNODIC_MONTH)))
