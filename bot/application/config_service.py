from bot.data.config_defaults import SCOPE_DEFAULT_ENABLED, TOGGLABLE_SCOPES
from bot.domain.commands.base import CommandConfig, CommandScope
from bot.domain.models.chat_config import ChatConfig, ChatPolicy
from bot.domain.models.command_data import CommandData
from bot.ports.config_store_port import ConfigStorePort


class ConfigService:
    def __init__(self, store: ConfigStorePort) -> None:
        self._store = store

    async def is_enabled(self, data: CommandData, config: CommandConfig) -> bool:
        if config.scope not in TOGGLABLE_SCOPES:
            return True
        chat_config = await self._store.load(data.platform or '', data.jid)
        return self._resolve(chat_config, config.name, config.scope)

    @staticmethod
    def _resolve(chat_config: ChatConfig, command_name: str, scope: CommandScope) -> bool:
        override = chat_config.override_for(command_name)
        if override is not None:
            return override
        if chat_config.policy is ChatPolicy.CURATED:
            return False
        return SCOPE_DEFAULT_ENABLED[scope]
