import random

import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Category, Command, CommandConfig, ParsedCommand
from bot.domain.constants import ADMIN_ONLY_COMMAND
from bot.domain.jid import strip_jid
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.group_admin import GroupAdminService

logger = structlog.get_logger()


class BanCommand(Command):
    BOT_NOT_ADMIN_MSG = 'Vai se foder! Eu não sou admin! 🖕'
    NOBODY_LEFT_MSG = 'Não sobrou ninguém pra eu banir! 🤷'

    def __init__(self, bot_jid: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._bot_jid = bot_jid

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='ban',
            args=ArgType.OPTIONAL,
            args_pattern=r'^(?:@\d+(?:\s+@\d+)*)?$',
            args_label='@número',
            group_only=True,
            category=Category.GROUP,
        )

    @property
    def menu_description(self) -> str:
        return 'Remove aleatoriamente um ou especificamente um ou mais participantes do grupo.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        metadata = await self.whatsapp.group_metadata(data.jid)
        participants = metadata['participants']
        owner = metadata.get('owner')

        bot_entry = next((p for p in participants if p['id'] == self._bot_jid), None)
        if not bot_entry or not bot_entry.get('admin'):
            return [Reply.to(data).text(self.BOT_NOT_ADMIN_MSG)]
        if not GroupAdminService.is_sender_admin(data, participants):
            return [Reply.to(data).text(ADMIN_ONLY_COMMAND)]

        if not data.mentioned_jids:
            return await self._ban_random(data, participants, owner)
        return await self._ban_mentioned(data, participants, data.mentioned_jids, owner)

    async def _ban_random(
        self,
        data: CommandData,
        participants: list[dict],
        owner: str | None,
    ) -> list[BotMessage]:
        candidates = [p['id'] for p in participants if p['id'] not in (self._bot_jid, owner)]
        if not candidates:
            return [Reply.to(data).text(self.NOBODY_LEFT_MSG)]
        target = random.choice(candidates)
        try:
            await self.whatsapp.group_participants_update(data.jid, [target], 'remove')
        except Exception:
            logger.exception('ban_random_error', jid=data.jid)
            return []
        return [Reply.to(data).text_with(f'Já era! @{strip_jid(target)} 👋😅', [target])]

    async def _ban_mentioned(
        self,
        data: CommandData,
        participants: list[dict],
        mentioned: list[str],
        owner: str | None,
    ) -> list[BotMessage]:
        owner_is_admin = any(p.get('admin') for p in participants if p['id'] == owner)
        messages: list[BotMessage] = []
        for jid in mentioned:
            if jid == self._bot_jid:
                continue
            if jid == owner and owner_is_admin:
                continue
            try:
                await self.whatsapp.group_participants_update(data.jid, [jid], 'remove')
            except Exception:
                logger.exception('ban_mentioned_error', jid=data.jid, target=jid)
                continue
            phone = strip_jid(jid)
            messages.append(Reply.to(data).text_with(f'Já era! @{phone} 👋😅', [jid]))
        return messages
