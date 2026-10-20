import json

import structlog

from bot.domain.services.group_welcome import GroupWelcomeService
from bot.domain.services.steal_group import StealGroupService
from bot.ports.broker_port import BrokerPort

logger = structlog.get_logger()


class GroupEventConsumer:
    QUEUE = 'group_events'

    def __init__(
        self,
        broker: BrokerPort,
        steal_group: StealGroupService,
        group_welcome: GroupWelcomeService,
    ) -> None:
        self._broker = broker
        self._handlers = {'promote': steal_group, 'joined': group_welcome}

    async def start(self) -> None:
        await self._broker.consume(self.QUEUE, self._handle)

    async def _handle(self, body: bytes) -> None:
        try:
            data = json.loads(body)
            handler = self._handlers.get(data.get('action'))
            if handler is None:
                return
            await handler.run(data)
        except Exception:
            logger.exception('group_event_error')
