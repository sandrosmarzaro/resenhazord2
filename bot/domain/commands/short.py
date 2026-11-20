import random
from typing import ClassVar

from bot.data.short_topics import SHORT_TOPICS
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
            aliases=['reels'],
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
        return 'Recebe um short aleatório do YouTube, ou um sobre o que você buscar.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        term = parsed.rest.strip() or random.choice(SHORT_TOPICS)
        try:
            return await self._send_random_short(data, term)
        except RuntimeError as error:
            raise DownloadError(self.DOWNLOAD_FAILED, detail=str(error)) from error

    async def _send_random_short(self, data: CommandData, term: str) -> list[BotMessage]:
        shorts = await YouTubeShorts.search(term)
        if not shorts:
            return [Reply.to(data).text(self.NO_RESULTS.format(term=term))]
        short = random.choice(shorts)
        video = await YtDlpService.download_merged(short.url)
        caption = f'{short.title} · {short.channel}'
        return [Reply.to(data).video_buffer(video, caption, gif_playback=Mp4.is_silent(video))]
