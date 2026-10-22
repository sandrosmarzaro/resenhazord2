import structlog

from bot.domain.models.command_data import CommandData
from bot.ports.agent_orchestrator_port import AgentOrchestratorPort
from bot.ports.agent_rate_limiter_port import AgentRateLimiterPort

logger = structlog.get_logger()


class ThrottledAgent:
    """Runs the agent unless the conversation used up its turns, so a bot on the
    other end of a DM cannot keep a reply loop alive."""

    def __init__(self, agent: AgentOrchestratorPort, limiter: AgentRateLimiterPort | None) -> None:
        self._agent = agent
        self._limiter = limiter

    async def run(self, data: CommandData) -> CommandData | None:
        conversation = f'{data.jid}:{data.participant or data.sender_jid}'
        if self._limiter and not await self._limiter.allow(conversation):
            logger.info('agent_rate_limited')
            return None
        return await self._agent.run(data)
