import pytest

from bot.domain.services.group_admin import GroupAdminService
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


def metadata(*participants: dict) -> dict:
    return {'participants': list(participants)}


class TestPrivateChat:
    @pytest.mark.anyio
    async def test_dm_sender_is_always_authorized(self):
        data = PrivateCommandDataFactory(platform='whatsapp')

        authorized = await GroupAdminService().is_authorized(data, whatsapp=None)

        assert authorized is True


class TestWhatsAppGroup:
    @pytest.mark.anyio
    async def test_admin_sender_is_authorized(self, mocker):
        sender = '5511999@s.whatsapp.net'
        data = GroupCommandDataFactory(platform='whatsapp', participant=sender)
        whatsapp = mocker.AsyncMock()
        whatsapp.group_metadata.return_value = metadata({'id': sender, 'admin': 'admin'})

        authorized = await GroupAdminService().is_authorized(data, whatsapp)

        assert authorized is True
        whatsapp.group_metadata.assert_awaited_once_with(data.jid)

    @pytest.mark.anyio
    async def test_non_admin_sender_is_rejected(self, mocker):
        sender = '5511999@s.whatsapp.net'
        data = GroupCommandDataFactory(platform='whatsapp', participant=sender)
        whatsapp = mocker.AsyncMock()
        whatsapp.group_metadata.return_value = metadata({'id': sender, 'admin': None})

        authorized = await GroupAdminService().is_authorized(data, whatsapp)

        assert authorized is False


class TestPreResolvedAdmin:
    @pytest.mark.anyio
    async def test_uses_is_admin_flag_when_present(self, mocker):
        data = GroupCommandDataFactory(platform='telegram', is_admin=True)
        whatsapp = mocker.AsyncMock()

        authorized = await GroupAdminService().is_authorized(data, whatsapp)

        assert authorized is True
        whatsapp.group_metadata.assert_not_called()


class TestUnsupported:
    @pytest.mark.anyio
    async def test_non_whatsapp_group_is_rejected(self, mocker):
        data = GroupCommandDataFactory(platform='discord')
        whatsapp = mocker.AsyncMock()

        authorized = await GroupAdminService().is_authorized(data, whatsapp)

        assert authorized is False
        whatsapp.group_metadata.assert_not_called()

    @pytest.mark.anyio
    async def test_whatsapp_group_without_port_is_rejected(self):
        data = GroupCommandDataFactory(platform='whatsapp')

        authorized = await GroupAdminService().is_authorized(data, whatsapp=None)

        assert authorized is False
