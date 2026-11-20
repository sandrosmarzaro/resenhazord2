from bot.domain.dev_key import DevKey
from tests.factories.command_data import GroupCommandDataFactory


class TestOf:
    def test_whatsapp_sender_is_its_jid(self):
        data = GroupCommandDataFactory(platform='whatsapp', sender_jid='5511999@lid')

        assert DevKey.of(data) == '5511999@lid'

    def test_discord_sender_is_namespaced(self):
        data = GroupCommandDataFactory(platform='discord', sender_jid='123456')

        assert DevKey.of(data) == 'discord:123456'

    def test_telegram_sender_is_namespaced(self):
        data = GroupCommandDataFactory(platform='telegram', sender_jid='987')

        assert DevKey.of(data) == 'telegram:987'
