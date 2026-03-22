import re
from collections.abc import Awaitable, Callable

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.jid import strip_jid
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.group_mentions import GroupMentionsService

SubHandler = Callable[[CommandData, str], Awaitable[list[BotMessage]]]


class GroupMentionsCommand(Command):
    RESERVED_KEYWORDS: frozenset[str] = frozenset(
        {'add', 'exit', 'create', 'delete', 'rename', 'list'}
    )
    MAX_GROUP_NAME_LEN = 15
    MENTION_PATTERN = re.compile(r'\s*@\d+\s*')

    def __init__(self, service: GroupMentionsService | None = None) -> None:
        super().__init__()
        self._service = service or GroupMentionsService()
        self._handlers: dict[str, SubHandler] = {
            'create': self._handle_create,
            'rename': self._handle_rename,
            'delete': self._handle_delete,
            'list': self._handle_list,
            'add': self._handle_add,
            'exit': self._handle_exit,
        }

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='grupo',
            aliases=['group'],
            args=ArgType.OPTIONAL,
            args_label='subcomando',
            group_only=True,
            category='group',
        )

    @property
    def menu_description(self) -> str:
        return 'Comando complexo. Use *,menu grupo* para detalhes.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        rest = parsed.rest
        for keyword, handler in self._handlers.items():
            if re.search(keyword, rest, re.IGNORECASE):
                sub_rest = re.sub(keyword, '', rest, count=1, flags=re.IGNORECASE)
                sub_rest = sub_rest.replace('\n', '').strip()
                return await handler(data, sub_rest)
        return await self._handle_mention(data, rest)

    def _validate_group_name(self, data: CommandData, name: str) -> BotMessage | None:
        if len(name) > self.MAX_GROUP_NAME_LEN:
            return Reply.to(data).text('O nome do grupo é desse tamanho! ✋    🤚')
        if any(re.search(kw, name, re.IGNORECASE) for kw in self.RESERVED_KEYWORDS):
            return Reply.to(data).text('O nome do grupo não pode ser um comando!')
        if re.search(r'\s', name):
            return Reply.to(data).text('O nome do grupo não pode ter espaço!')
        return None

    async def _handle_create(self, data: CommandData, rest: str) -> list[BotMessage]:
        group_name = self.MENTION_PATTERN.sub('', rest)
        if not group_name:
            return [Reply.to(data).text('Cadê o nome do grupo? 🤔')]
        error = self._validate_group_name(data, group_name)
        if error:
            return [error]

        result = await self._service.create(
            data.jid, data.sender_jid, group_name, data.mentioned_jids
        )
        if not result['ok']:
            return [Reply.to(data).text(result['message'])]
        return [Reply.to(data).text(f'Grupo *{result["group_name"]}* criado com sucesso! 🎉')]

    async def _handle_rename(self, data: CommandData, rest: str) -> list[BotMessage]:
        if not re.match(r'\S+\s+\S+', rest):
            return [Reply.to(data).text('Cadê os nomes dos grupos? 🤔')]
        parts = rest.split()
        old_name, new_name = parts[0], parts[1]
        error = self._validate_group_name(data, new_name)
        if error:
            return [error]

        result = await self._service.rename(data.jid, old_name, new_name)
        if not result['ok']:
            return [Reply.to(data).text(result['message'])]
        old = result['old_name']
        new = result['new_name']
        return [Reply.to(data).text(f'Grupo *{old}* renomeado para *{new}* com sucesso! 🎉')]

    async def _handle_delete(self, data: CommandData, rest: str) -> list[BotMessage]:
        if not rest:
            return [Reply.to(data).text('Cadê o nome do grupo? 🤔')]
        result = await self._service.delete(data.jid, rest)
        if not result['ok']:
            return [Reply.to(data).text(result['message'])]
        return [Reply.to(data).text(f'Grupo *{result["group_name"]}* deletado com sucesso! 🎉')]

    async def _handle_list(self, data: CommandData, rest: str) -> list[BotMessage]:
        if not rest:
            result = await self._service.list_all(data.jid)
            if not result['ok']:
                return [Reply.to(data).text(result['message'])]
            lines = [f'- _{g["name"]}_' for g in result['groups']]
            return [Reply.to(data).text('📜 *GRUPOS* 📜\n\n' + '\n'.join(lines))]

        result = await self._service.list_one(data.jid, rest)
        if not result['ok']:
            return [Reply.to(data).text(result['message'])]
        lines = [f'- {i + 1}: @{strip_jid(p)}' for i, p in enumerate(result['participants'])]
        return [
            Reply.to(data).text_with(
                f'📜 *{rest.upper()}* 📜\n\n' + '\n'.join(lines),
                result['participants'],
            )
        ]

    async def _handle_add(self, data: CommandData, rest: str) -> list[BotMessage]:
        group_name = self.MENTION_PATTERN.sub('', rest)
        if not group_name:
            return [Reply.to(data).text('Cadê o nome do grupo? 🤔')]

        result = await self._service.add(data.jid, group_name, data.sender_jid, data.mentioned_jids)
        if not result['ok']:
            return [Reply.to(data).text(result['message'])]
        if result['self_only']:
            text = f'Você foi adicionado ao grupo *{result["group_name"]}* com sucesso! 🎉'
        else:
            text = f'Participantes adicionados ao grupo *{result["group_name"]}* com sucesso! 🎉'
        return [Reply.to(data).text(text)]

    async def _handle_exit(self, data: CommandData, rest: str) -> list[BotMessage]:
        parts = rest.split()
        group_name = parts[0] if parts else ''
        if not group_name:
            return [Reply.to(data).text('Cadê o nome do grupo? 🤔')]
        indices = [int(p) for p in parts[1:] if p.isdigit()]

        result = await self._service.exit(data.jid, group_name, data.sender_jid, indices)
        if not result['ok']:
            return [Reply.to(data).text(result['message'])]
        if result['self_only']:
            text = f'Você foi removido do grupo *{result["group_name"]}* com sucesso! 🎉'
        else:
            text = f'Participantes removidos do grupo *{result["group_name"]}* com sucesso! 🎉'
        return [Reply.to(data).text(text)]

    async def _handle_mention(self, data: CommandData, rest: str) -> list[BotMessage]:
        parts = rest.split(maxsplit=1)
        group_name = parts[0] if parts else ''
        text = parts[1] if len(parts) > 1 else ''

        result = await self._service.mention(data.jid, group_name)
        if not result['ok']:
            return [Reply.to(data).text(result['message'])]

        participants = result['participants']
        mentions = [f'@{strip_jid(p)}' for p in participants]
        prefix = f'{text}\n\n' if text else ''
        return [Reply.to(data).text_with(f'{prefix}{" ".join(mentions)}', participants)]
