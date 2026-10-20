import pytest

from bot.data.welcome_messages import WHATSAPP_WELCOME
from bot.domain.services.group_welcome import GroupWelcomeService


class TestGroupWelcome:
    @pytest.mark.anyio
    async def test_greets_the_group_the_bot_joined(self, mock_whatsapp):
        service = GroupWelcomeService(mock_whatsapp)

        await service.run({'id': 'joined@g.us', 'action': 'joined'})

        mock_whatsapp.send_message.assert_awaited_once_with(
            'joined@g.us', {'text': WHATSAPP_WELCOME}
        )

    def test_welcome_points_to_the_menu(self):
        assert ',menu' in WHATSAPP_WELCOME
