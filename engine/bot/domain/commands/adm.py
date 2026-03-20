"""Adm command — insult all group administrators with a random swearing."""

import random

import structlog

from bot.data.swearings import SWEARINGS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.jid import strip_jid
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage

logger = structlog.get_logger()


class AdmCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='adm', group_only=True, category='grupo')

    @property
    def menu_description(self) -> str:
        return 'Xingue aleatoriamente todos os administradores do grupo.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        metadata = await self._whatsapp.group_metadata(data.jid)
        admins = [p for p in metadata['participants'] if p.get('admin')]
        admin_jids = [a['id'] for a in admins]
        admin_mentions = [f'@{strip_jid(a["id"])} ' for a in admins]
        swearing = random.choice(SWEARINGS)  # noqa: S311
        logger.info('adm_command', jid=data.jid, admin_count=len(admins))
        text = f'Vai se foder administração! 🖕\nVocê é {swearing}\n{"".join(admin_mentions)}'
        return [Reply.to(data).text_with(text, admin_jids)]
