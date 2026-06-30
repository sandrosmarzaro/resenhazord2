from collections.abc import Awaitable, Callable
from typing import ClassVar

from bot.application.command_registry import CommandRegistry
from bot.data.config_defaults import NSFW_SUBTYPE, SUBTYPE_CATEGORIES, TOGGLABLE_SCOPES
from bot.domain.commands.base import Command, CommandScope
from bot.domain.models.chat_config import ChatConfig, ChatKey, ChatPolicy, ChatType
from bot.domain.models.command_data import CommandData
from bot.infrastructure.cached_config_store import CachedConfigStore
from bot.ports.config_store_port import ConfigStorePort

Handler = Callable[[CommandData, str], Awaitable[str]]


class ConfigEditor:
    _HELP: ClassVar[str] = (
        'Use: *,config on|off|reset <comando|nsfw|download|group|random|info>* '
        'ou *,config policy open|curated*.'
    )
    _INVALID: ClassVar[str] = '❓ Não reconheço *{token}* como comando ou tipo configurável.'
    _UNKNOWN_POLICY: ClassVar[str] = '❓ Política inválida. Use *open* ou *curated*.'

    def __init__(
        self,
        store: ConfigStorePort | None = None,
        registry: CommandRegistry | None = None,
    ) -> None:
        self._store = store or CachedConfigStore.instance()
        self._registry = registry or CommandRegistry.instance()
        self._verbs: dict[str, Handler] = {
            'on': self._enable,
            'off': self._disable,
            'reset': self._reset,
            'policy': self._set_policy,
        }

    async def apply(self, data: CommandData, rest: str) -> str:
        tokens = rest.split()
        if not tokens:
            return await self._render(data)
        handler = self._verbs.get(tokens[0].lower())
        if handler is None:
            return self._HELP
        argument = tokens[1] if len(tokens) > 1 else ''
        return await handler(data, argument)

    async def _enable(self, data: CommandData, token: str) -> str:
        return await self._write_override(data, token, enabled=True, label='✅ Ativado')

    async def _disable(self, data: CommandData, token: str) -> str:
        return await self._write_override(data, token, enabled=False, label='🚫 Desativado')

    async def _write_override(
        self, data: CommandData, token: str, *, enabled: bool, label: str
    ) -> str:
        targets = self._resolve(token)
        if not targets:
            return self._INVALID.format(token=token)
        key = self._key(data)
        for name in targets:
            await self._store.set_override(key, name, enabled=enabled)
        return f'{label}: {", ".join(targets)}'

    async def _reset(self, data: CommandData, token: str) -> str:
        targets = self._resolve(token)
        if not targets:
            return self._INVALID.format(token=token)
        key = self._key(data)
        for name in targets:
            await self._store.clear_override(key, name)
        return f'↩️ Resetado ao padrão: {", ".join(targets)}'

    async def _set_policy(self, data: CommandData, token: str) -> str:
        if token.lower() not in ChatPolicy.__members__.values():
            return self._UNKNOWN_POLICY
        policy = ChatPolicy(token.lower())
        await self._store.set_policy(self._key(data), policy)
        return f'⚙️ Política deste chat: *{policy.value}*'

    async def _render(self, data: CommandData) -> str:
        config = await self._store.load(data.platform or '', data.jid)
        return self._format_status(config)

    def _resolve(self, token: str) -> list[str]:
        token = token.lower()
        if token == NSFW_SUBTYPE:
            return [c.config.name for c in self._togglable() if c.config.scope == CommandScope.NSFW]
        category = SUBTYPE_CATEGORIES.get(token)
        if category is not None:
            return [c.config.name for c in self._togglable() if c.config.category == category]
        command = self._registry.get_by_name(token)
        if command is not None and command.config.scope in TOGGLABLE_SCOPES:
            return [command.config.name]
        return []

    def _togglable(self) -> list[Command]:
        return [c for c in self._registry.get_all() if c.config.scope in TOGGLABLE_SCOPES]

    @staticmethod
    def _key(data: CommandData) -> ChatKey:
        chat_type = ChatType.GROUP if data.is_group else ChatType.PRIVATE
        return ChatKey(platform=data.platform or '', native_id=data.jid, type=chat_type)

    @staticmethod
    def _format_status(config: ChatConfig) -> str:
        enabled = sorted(name for name, on in config.overrides.items() if on)
        disabled = sorted(name for name, on in config.overrides.items() if not on)
        lines = [f'*Config deste chat* (política: {config.policy.value})']
        lines.append(f'✅ {", ".join(enabled)}' if enabled else '✅ —')
        lines.append(f'🚫 {", ".join(disabled)}' if disabled else '🚫 —')
        return '\n'.join(lines)
