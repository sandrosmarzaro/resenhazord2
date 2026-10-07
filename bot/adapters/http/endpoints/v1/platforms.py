"""Chat platform connection status."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from bot.adapters.http.schemas import PlatformResponse
from bot.infrastructure.platform_supervisor import PlatformSupervisor

router = APIRouter(prefix='/v1/ops/platforms')


def platform_supervisor(request: Request) -> PlatformSupervisor:
    return request.app.state.platforms


@router.get('')
async def list_platforms(
    supervisor: Annotated[PlatformSupervisor, Depends(platform_supervisor)],
) -> list[PlatformResponse]:
    return [
        PlatformResponse(name=name, status=status) for name, status in supervisor.statuses().items()
    ]
