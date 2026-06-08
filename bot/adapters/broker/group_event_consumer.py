"""Consumes group events from the broker and dispatches to StealGroupService."""

import json

import structlog

from bot.domain.services.steal_group import StealGroupService
from bot.ports.broker_port import BrokerPort

logger = structlog.get_logger()


class GroupEventConsumer:
    QUEUE = 'group_events'

    def __init__(self, broker: BrokerPort, steal_group: StealGroupService) -> None:
        self._broker = broker
        self._steal_group = steal_group

    async def start(self) -> None:
        await self._broker.consume(self.QUEUE, self._handle)

    async def _handle(self, body: bytes) -> None:
        try:
            data = json.loads(body)
            await self._steal_group.run(data)
        except Exception:
            logger.exception('group_event_error')
