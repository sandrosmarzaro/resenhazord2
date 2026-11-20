import random
from typing import ClassVar

import httpx

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    ArgType,
    Category,
    Command,
    CommandConfig,
    Flag,
    ParsedCommand,
    Platform,
)
from bot.domain.exceptions import DownloadError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.instagram_reels import InstagramReels
from bot.domain.services.mp4 import Mp4
from bot.domain.services.ytdlp import YtDlpService


class ReelsCommand(Command):
    DOWNLOAD_FAILED: ClassVar[str] = 'Não consegui baixar um reels agora, tenta de novo! 😅'

    def __init__(self, cookies_path: str = '') -> None:
        super().__init__()
        self._cookies_path = cookies_path

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='reels',
            flags=[Flag.SHOW, Flag.DM],
            args=ArgType.NONE,
            category=Category.RANDOM,
            platforms=[Platform.ALL],
            # Same memory bound as ,dl: the video rides the reply as base64.
            exclusive=True,
        )

    @property
    def menu_description(self) -> str:
        return 'Recebe um reels aleatório do feed do Instagram.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            return await self._send_random_reel(data)
        except (RuntimeError, httpx.HTTPError) as error:
            raise DownloadError(self.DOWNLOAD_FAILED, detail=str(error)) from error

    async def _send_random_reel(self, data: CommandData) -> list[BotMessage]:
        reels = await InstagramReels.feed()
        # Instagram serves reels as one mp4 with both streams, the same path ,dl takes.
        video, title = await YtDlpService.download(random.choice(reels), self._cookies_path)
        return [Reply.to(data).video_buffer(video, title, gif_playback=Mp4.is_silent(video))]
