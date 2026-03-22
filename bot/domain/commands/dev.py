import re

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    ArgType,
    Command,
    CommandConfig,
    CommandScope,
    ParsedCommand,
)
from bot.domain.jid import strip_jid
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.dev_list import DevListService


class DevCommand(Command):
    JID_PATTERN = re.compile(r'@?(\d+)')

    def __init__(self, service: DevListService | None = None) -> None:
        super().__init__()
        self._service = service or DevListService()

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='dev',
            scope=CommandScope.DEV,
            args=ArgType.OPTIONAL,
        )

    @property
    def menu_description(self) -> str:
        return 'Gerencia a lista de desenvolvedores.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        rest = parsed.rest.strip()

        if rest.startswith('add'):
            return await self._handle_add(data, rest[3:].strip())
        if rest.startswith('remove'):
            return await self._handle_remove(data, rest[6:].strip())
        return await self._handle_list(data)

    async def _handle_add(self, data: CommandData, rest: str) -> list[BotMessage]:
        jid = self._extract_jid(rest, data)
        if not jid:
            return [Reply.to(data).text('Uso: ,dev add @número')]
        added = await self._service.add(jid)
        phone = strip_jid(jid)
        if added:
            return [Reply.to(data).text(f'@{phone} adicionado como dev 🛠️')]
        return [Reply.to(data).text(f'@{phone} já é dev')]

    async def _handle_remove(self, data: CommandData, rest: str) -> list[BotMessage]:
        jid = self._extract_jid(rest, data)
        if not jid:
            return [Reply.to(data).text('Uso: ,dev remove @número')]
        removed = await self._service.remove(jid)
        phone = strip_jid(jid)
        if removed:
            return [Reply.to(data).text(f'@{phone} removido da lista de devs')]
        return [Reply.to(data).text(f'@{phone} não é dev')]

    async def _handle_list(self, data: CommandData) -> list[BotMessage]:
        devs = await self._service.list_all()
        if not devs:
            return [Reply.to(data).text('Nenhum dev cadastrado.')]
        lines = [f'- @{strip_jid(jid)}' for jid in devs]
        return [Reply.to(data).text_with('🛠️ *Devs* 🛠️\n\n' + '\n'.join(lines), devs)]

    def _extract_jid(self, rest: str, data: CommandData) -> str | None:
        if data.mentioned_jids:
            return data.mentioned_jids[0]
        match = self.JID_PATTERN.search(rest)
        if match:
            return f'{match.group(1)}@s.whatsapp.net'
        return None
