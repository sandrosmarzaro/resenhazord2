import base64
import json

import pytest

from bot.adapters.whatsapp.broker_client import BrokerWhatsAppClient
from tests.fixtures.mock_broker import MockBrokerPort


def _action(broker: MockBrokerPort, index: int = 0) -> dict:
    queue, body = broker.published[index]
    assert queue == 'wa_actions'
    return json.loads(body)


class TestFireAndForgetWrites:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_group_participants_update_publishes_action(self):
        broker = MockBrokerPort()
        client = BrokerWhatsAppClient(broker)

        result = await client.group_participants_update('g@g.us', ['u@s'], 'remove')

        assert result == []
        assert _action(broker) == {
            'method': 'group_participants_update',
            'jid': 'g@g.us',
            'participants': ['u@s'],
            'action': 'remove',
        }

    @pytest.mark.anyio
    async def test_send_message_publishes_action(self):
        broker = MockBrokerPort()
        client = BrokerWhatsAppClient(broker)

        result = await client.send_message('g@g.us', {'text': 'oi'})

        assert result == {}
        action = _action(broker)
        assert action['method'] == 'send_message'
        assert action['content'] == {'text': 'oi'}

    @pytest.mark.anyio
    async def test_update_profile_picture_encodes_image(self):
        broker = MockBrokerPort()
        client = BrokerWhatsAppClient(broker)

        await client.update_profile_picture('g@g.us', b'\x01\x02')

        action = _action(broker)
        assert action['method'] == 'update_profile_picture'
        assert action['image'] == base64.b64encode(b'\x01\x02').decode()

    @pytest.mark.anyio
    async def test_presence_update_publishes_action(self):
        broker = MockBrokerPort()
        client = BrokerWhatsAppClient(broker)

        await client.send_presence_update('composing', 'g@g.us')

        assert _action(broker) == {
            'method': 'send_presence_update',
            'type': 'composing',
            'jid': 'g@g.us',
        }
