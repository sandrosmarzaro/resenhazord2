import pytest
from structlog.testing import capture_logs

from bot.domain.models.chat_config import ChatConfig
from bot.domain.services.group_admin import GroupAdminService
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


def metadata(*participants: dict) -> dict:
    return {'participants': list(participants)}


@pytest.fixture
def store(mocker):
    store = mocker.AsyncMock()
    store.load.return_value = ChatConfig()
    return store


@pytest.fixture
def service(mock_dev_list, store):
    return GroupAdminService(dev_list=mock_dev_list, store=store)


class TestPrivateChat:
    @pytest.mark.anyio
    async def test_dm_sender_is_always_authorized(self, service):
        data = PrivateCommandDataFactory(platform='whatsapp')

        authorized = await service.is_authorized(data, whatsapp=None)

        assert authorized is True


class TestWhatsAppGroup:
    @pytest.mark.anyio
    async def test_admin_sender_is_authorized(self, service, mocker):
        sender = '5511999@s.whatsapp.net'
        data = GroupCommandDataFactory(platform='whatsapp', participant=sender)
        whatsapp = mocker.AsyncMock()
        whatsapp.group_metadata.return_value = metadata({'id': sender, 'admin': 'admin'})

        authorized = await service.is_authorized(data, whatsapp)

        assert authorized is True
        whatsapp.group_metadata.assert_awaited_once_with(data.jid)

    @pytest.mark.anyio
    async def test_non_admin_sender_is_rejected(self, service, mocker):
        sender = '5511999@s.whatsapp.net'
        data = GroupCommandDataFactory(platform='whatsapp', participant=sender)
        whatsapp = mocker.AsyncMock()
        whatsapp.group_metadata.return_value = metadata({'id': sender, 'admin': None})

        authorized = await service.is_authorized(data, whatsapp)

        assert authorized is False


class TestPreResolvedAdmin:
    @pytest.mark.anyio
    async def test_uses_is_admin_flag_when_present(self, service, mocker):
        data = GroupCommandDataFactory(platform='telegram', is_admin=True)
        whatsapp = mocker.AsyncMock()

        authorized = await service.is_authorized(data, whatsapp)

        assert authorized is True
        whatsapp.group_metadata.assert_not_called()


class TestUnsupported:
    @pytest.mark.anyio
    async def test_non_whatsapp_group_is_rejected(self, service, mocker):
        data = GroupCommandDataFactory(platform='discord')
        whatsapp = mocker.AsyncMock()

        authorized = await service.is_authorized(data, whatsapp)

        assert authorized is False
        whatsapp.group_metadata.assert_not_called()

    @pytest.mark.anyio
    async def test_whatsapp_group_without_port_is_rejected(self, service):
        data = GroupCommandDataFactory(platform='whatsapp')

        authorized = await service.is_authorized(data, whatsapp=None)

        assert authorized is False


class TestDevBypass:
    @pytest.mark.anyio
    async def test_dev_passes_where_the_chat_allows_it(self, service, mock_dev_list, store):
        store.load.return_value = ChatConfig(dev_admin=True)
        mock_dev_list.is_dev.return_value = True
        data = GroupCommandDataFactory(platform='telegram', sender_jid='42', is_admin=False)

        authorized = await service.is_authorized(data, whatsapp=None)

        assert authorized is True
        store.load.assert_awaited_once_with('telegram', data.jid)
        mock_dev_list.is_dev.assert_awaited_once_with('telegram:42')

    @pytest.mark.anyio
    async def test_dev_is_refused_where_the_chat_does_not_allow_it(self, service, mock_dev_list):
        mock_dev_list.is_dev.return_value = True
        data = GroupCommandDataFactory(platform='whatsapp', is_admin=False)

        authorized = await service.is_authorized(data, whatsapp=None)

        assert authorized is False

    @pytest.mark.anyio
    async def test_non_dev_is_refused_even_where_the_chat_allows_it(self, service, store):
        store.load.return_value = ChatConfig(dev_admin=True)
        data = GroupCommandDataFactory(platform='whatsapp', is_admin=False)

        authorized = await service.is_authorized(data, whatsapp=None)

        assert authorized is False

    @pytest.mark.anyio
    async def test_admin_skips_the_dev_lookup(self, service, mock_dev_list, store):
        data = GroupCommandDataFactory(platform='discord', is_admin=True)

        authorized = await service.is_authorized(data, whatsapp=None)

        assert authorized is True
        store.load.assert_not_called()
        mock_dev_list.is_dev.assert_not_called()

    @pytest.mark.anyio
    async def test_logs_a_pass_granted_only_by_the_bypass(self, service, mock_dev_list, store):
        store.load.return_value = ChatConfig(dev_admin=True)
        mock_dev_list.is_dev.return_value = True
        data = GroupCommandDataFactory(platform='discord', sender_jid='7', is_admin=False)

        with capture_logs() as logs:
            await service.is_authorized(data, whatsapp=None)

        assert [(log['event'], log['chat'], log['dev']) for log in logs] == [
            ('dev_admin_bypass', data.jid, 'discord:7')
        ]


class TestIsAdmin:
    @pytest.mark.anyio
    async def test_dev_bypass_does_not_count(self, service, mock_dev_list, store):
        store.load.return_value = ChatConfig(dev_admin=True)
        mock_dev_list.is_dev.return_value = True
        data = GroupCommandDataFactory(platform='telegram', is_admin=False)

        admin = await service.is_admin(data, whatsapp=None)

        assert admin is False

    @pytest.mark.anyio
    async def test_real_admin_counts(self, service):
        data = GroupCommandDataFactory(platform='telegram', is_admin=True)

        admin = await service.is_admin(data, whatsapp=None)

        assert admin is True
