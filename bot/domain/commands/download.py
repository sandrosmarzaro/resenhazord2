import re

import structlog

from bot.data.download_errors import (
    FALLBACK_MESSAGE,
    NO_VIDEO_IN_POST,
    YTDLP_ERROR_MESSAGES,
)
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
from bot.domain.services.ytdlp import YtDlpService

logger = structlog.get_logger()


class DownloadCommand(Command):
    URL_REGEX = re.compile(r'https?://\S+')

    def __init__(self, cookies_path: str = '') -> None:
        super().__init__()
        self._cookies_path = cookies_path

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='dl',
            aliases=['baixar'],
            flags=[Flag.SHOW, Flag.DM],
            args=ArgType.REQUIRED,
            args_pattern=r'https?://\S+[\s\S]*',
            args_label='url',
            category=Category.DOWNLOAD,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Baixe vídeos e fotos de qualquer URL (YouTube, Instagram, TikTok, etc.).'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        match = self.URL_REGEX.search(parsed.rest)
        url = match.group(0) if match else parsed.rest

        try:
            return [await self._download(data, url)]
        except RuntimeError as e:
            raise DownloadError(self._match_error(str(e)), detail=str(e)) from e
        except DownloadError:
            raise
        except Exception as e:
            raise DownloadError(FALLBACK_MESSAGE, detail=str(e)) from e

    async def _download(self, data: CommandData, url: str) -> BotMessage:
        try:
            video_buffer, title = await YtDlpService.download(url, self._cookies_path)
        except RuntimeError as e:
            if NO_VIDEO_IN_POST not in str(e):
                raise
            image_buffer, title = await YtDlpService.download_image(url, self._cookies_path)
            return Reply.to(data).image_buffer(image_buffer, title)

        return Reply.to(data).video_buffer(video_buffer, title)

    @staticmethod
    def _match_error(error: str) -> str:
        for pattern, message in YTDLP_ERROR_MESSAGES.items():
            if pattern in error:
                return message
        return FALLBACK_MESSAGE
