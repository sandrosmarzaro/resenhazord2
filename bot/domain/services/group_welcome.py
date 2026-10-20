from bot.adapters.whatsapp.port import WhatsAppPort
from bot.data.welcome_messages import WHATSAPP_WELCOME


class GroupWelcomeService:
    def __init__(self, whatsapp: WhatsAppPort) -> None:
        self._whatsapp = whatsapp

    async def run(self, data: dict) -> None:
        await self._whatsapp.send_message(data['id'], {'text': WHATSAPP_WELCOME})
