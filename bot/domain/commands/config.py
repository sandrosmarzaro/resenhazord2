from typing import ClassVar

from bot.application.config_editor import ConfigEditor
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    ArgType,
    Category,
    Command,
    CommandConfig,
    CommandScope,
    ParsedCommand,
    Platform,
)
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.group_admin import GroupAdminService


class ConfigCommand(Command):
    _NOT_ADMIN_MSG: ClassVar[str] = 'Só admin configura os comandos do chat. 🙅'
    _ADMIN_ONLY: ClassVar[tuple[str, ...]] = ('dev', 'on')

    def __init__(
        self,
        admin: GroupAdminService | None = None,
        editor: ConfigEditor | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._admin = admin or GroupAdminService()
        self._editor = editor or ConfigEditor()

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='config',
            args=ArgType.OPTIONAL,
            args_label='subcomando',
            scope=CommandScope.ADMIN,
            category=Category.GROUP,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return (
            'Liga/desliga comandos neste chat (só admin). Use *,config on nsfw* para liberar'
            ' os +18, *,config on|off|reset <comando|nsfw|download|group|random|info>*'
            ', *,config dev on|off* para deixar devs configurarem o grupo'
            ' ou *,config* para ver o estado.'
        )

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if not await self._is_allowed(data, parsed.rest):
            return [Reply.to(data).text(self._NOT_ADMIN_MSG)]
        response = await self._editor.apply(data, parsed.rest)
        return [Reply.to(data).text(response)]

    async def _is_allowed(self, data: CommandData, rest: str) -> bool:
        # Turning the bypass on takes a real admin, or any dev could grant it to themselves.
        if tuple(rest.lower().split()[:2]) == self._ADMIN_ONLY:
            return await self._admin.is_admin(data, self._whatsapp)
        return await self._admin.is_authorized(data, self._whatsapp)
