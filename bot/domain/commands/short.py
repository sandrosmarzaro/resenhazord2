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
from bot.domain.services.mp4 import Mp4
from bot.domain.services.youtube_shorts import YouTubeShorts
from bot.domain.services.ytdlp import YtDlpService


class ShortCommand(Command):
    NO_RESULTS: ClassVar[str] = 'Não achei nenhum short sobre *{term}* 😕'
    DOWNLOAD_FAILED: ClassVar[str] = 'Não consegui baixar um short agora, tenta de novo! 😅'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='short',
            flags=[Flag.SHOW, Flag.DM],
            args=ArgType.OPTIONAL,
            args_label='busca',
            category=Category.RANDOM,
            platforms=[Platform.ALL],
            # Same memory bound as ,dl: the video rides the reply as base64.
            exclusive=True,
        )

    @property
    def menu_description(self) -> str:
        return 'Recebe um short aleatório do feed do YouTube, ou um sobre o que você buscar.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            return await self._send_random_short(data, parsed.rest.strip())
        except (RuntimeError, httpx.HTTPError) as error:
            raise DownloadError(self.DOWNLOAD_FAILED, detail=str(error)) from error

    async def _send_random_short(self, data: CommandData, term: str) -> list[BotMessage]:
        shorts = await YouTubeShorts.search(term) if term else await YouTubeShorts.feed()
        if not shorts:
            return [Reply.to(data).text(self.NO_RESULTS.format(term=term))]
        video, caption = await YtDlpService.download_merged(random.choice(shorts))
        return [Reply.to(data).video_buffer(video, caption, gif_playback=Mp4.is_silent(video))]
