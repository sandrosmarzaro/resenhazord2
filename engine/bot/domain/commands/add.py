"""Add command — add a random or specific phone number to a WhatsApp group."""

import random

import structlog

from bot.data.ddd_list import DDD_LIST, EIGHT_DIGIT_PREFIXES
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage

logger = structlog.get_logger()


class AddCommand(Command):
    COUNTRY_CODE = '55'
    MAX_PHONE_LENGTH = 11
    MIN_COMPLETE_PHONE_LENGTH = 10
    BOT_NOT_ADMIN_MSG = 'Vai se fuder! Eu não sou admin! 🖕'
    INVALID_DDD_MSG = 'Burro burro! O DDD do estado 🏳️\u200d🌈 não existe!'
    PHONE_TOO_LONG_MSG = 'Aiiiiii, o tamanho do telefone é desse ✋   🤚 tamanho, só aguento 11cm'

    def __init__(self, bot_jid: str = '', **kwargs) -> None:
        super().__init__(**kwargs)
        self._bot_jid = bot_jid

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='add',
            args=ArgType.OPTIONAL,
            args_pattern=r'^(?:\d+)?$',
            args_label='número',
            group_only=True,
            category='grupo',
        )

    @property
    def menu_description(self) -> str:
        return 'Adiciona um número ao grupo. Aleatório ou específico.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        metadata = await self._whatsapp.group_metadata(data.jid)
        participants = metadata['participants']

        bot_entry = next((p for p in participants if p['id'] == self._bot_jid), None)
        if not bot_entry or not bot_entry.get('admin'):
            return [Reply.to(data).text(self.BOT_NOT_ADMIN_MSG)]

        phone = parsed.rest.strip()
        if not phone:
            return await self._add_random_phone(data)

        if not any(phone.startswith(ddd) for ddd in DDD_LIST):
            return [Reply.to(data).text(self.INVALID_DDD_MSG)]

        messages: list[BotMessage] = []
        if len(phone) > self.MAX_PHONE_LENGTH:
            messages.append(Reply.to(data).text(self.PHONE_TOO_LONG_MSG))

        result = await self._add_phone(data, phone)
        messages.extend(result)
        return messages

    async def _add_random_phone(self, data: CommandData) -> list[BotMessage]:
        while True:
            ddd = random.choice(DDD_LIST)  # noqa: S311
            prefix = '8' if ddd in EIGHT_DIGIT_PREFIXES else '9'
            phone = ddd + prefix

            size = random.choice([self.MAX_PHONE_LENGTH - 1, self.MAX_PHONE_LENGTH])  # noqa: S311
            while len(phone) < size:
                phone += str(random.randint(0, 9))  # noqa: S311

            consult = await self._whatsapp.on_whatsapp([f'{self.COUNTRY_CODE}{phone}'])
            if consult and consult[0].get('exists'):
                try:
                    await self._whatsapp.group_participants_update(
                        data.jid, [consult[0]['jid']], 'add'
                    )
                except Exception:
                    logger.exception('add_random_phone_error', jid=data.jid, phone=phone)
                    return [Reply.to(data).text(f'Não consegui adicionar o número {phone} 😔')]
                return []

    async def _add_phone(self, data: CommandData, phone: str) -> list[BotMessage]:
        consult = await self._whatsapp.on_whatsapp([f'{self.COUNTRY_CODE}{phone}'])
        has_whatsapp = consult and consult[0].get('exists')
        jid = consult[0]['jid'] if has_whatsapp else f'{self.COUNTRY_CODE}{phone}@lid'
        try:
            await self._whatsapp.group_participants_update(data.jid, [jid], 'add')
        except Exception:
            logger.exception('add_phone_error', jid=data.jid, phone=phone)
            return [Reply.to(data).text(f'Não consegui adicionar o número {phone} 😔')]
        return []
