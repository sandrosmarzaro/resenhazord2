from typing import ClassVar

from bot.application.command_registry import CommandRegistry
from bot.data.menu_messages import (
    ALEATORIA_SUBHEADER,
    CATEGORY_HEADERS,
    CATEGORY_ORDER,
    MENU_BIBLIA,
    MENU_GRUPO,
)
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, OptionDef, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class MenuCommand(Command):
    SECTION_MENUS: ClassVar[dict[str, str]] = {
        'grupo': MENU_GRUPO,
        'bíblia': MENU_BIBLIA,
    }

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='menu',
            options=[OptionDef(name='section', values=['grupo', 'bíblia'])],
            flags=['dm'],
            category='other',
        )

    @property
    def menu_description(self) -> str:
        return 'Exibe o menu de comandos.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        section = parsed.options.get('section')
        if section and section in self.SECTION_MENUS:
            return [Reply.to(data).text(self.SECTION_MENUS[section])]
        return [Reply.to(data).text(self._build_menu())]

    def _build_menu(self) -> str:
        commands = CommandRegistry.instance().get_all()
        grouped: dict[str, list[Command]] = {}

        for cmd in commands:
            category = cmd.config.category
            if not category:
                continue
            grouped.setdefault(category, []).append(cmd)

        sections: list[str] = ['\t\t\t📝 *MENU DE COMANDOS* 📝']

        for category in CATEGORY_ORDER:
            cmds = grouped.get(category)
            if not cmds:
                continue

            header = CATEGORY_HEADERS[category]
            if category == 'random':
                header += ALEATORIA_SUBHEADER

            entries = [self._format_entry(cmd) for cmd in cmds]
            sections.append(f'{header}\n\n{"\n\n".join(entries)}')

        return '\n\n'.join(sections)

    @staticmethod
    def _format_entry(cmd: Command) -> str:
        names = [cmd.config.name, *cmd.config.aliases]
        names_formatted = ' ou '.join(f'*,{n}*' for n in names)
        options = MenuCommand._format_options(cmd.config)
        return f'- {names_formatted}{options}\n> {cmd.menu_description}'

    @staticmethod
    def _format_options(config: CommandConfig) -> str:
        parts: list[str] = [f'[{" | ".join(opt.values)}]' for opt in config.options if opt.values]
        parts.extend(f'+{f}' for f in config.flags if f not in {'dm', 'show'})

        label = config.args_label or 'texto'
        if config.args == ArgType.REQUIRED:
            parts.append(f'<{label}>')
        elif config.args == ArgType.OPTIONAL:
            parts.append(f'[{label}]')

        return f' {" ".join(parts)}' if parts else ''
