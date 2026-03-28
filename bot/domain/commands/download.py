import re

import structlog

from bot.data.download_errors import (
    FALLBACK_MESSAGE,
    YTDLP_ERROR_MESSAGES,
)
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.exceptions import DownloadError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.ytdlp import YtDlpService

logger = structlog.get_logger()


class DownloadCommand(Command):
    URL_REGEX = re.compile(r'https?://\S+')

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='dl',
            aliases=['baixar'],
            flags=['show', 'dm'],
            args=ArgType.REQUIRED,
            args_pattern=r'https?://\S+[\s\S]*',
            args_label='url',
            category='download',
            platforms=['whatsapp', 'discord'],
        )

    @property
    def menu_description(self) -> str:
        return 'Baixe vídeos de qualquer URL (YouTube, Instagram, TikTok, etc.).'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        match = self.URL_REGEX.search(parsed.rest)
        url = match.group(0) if match else parsed.rest

        try:
            video_buffer, title = await YtDlpService.download(url)
        except RuntimeError as e:
            raise DownloadError(self._match_error(str(e)), detail=str(e)) from e
        except DownloadError:
            raise
        except Exception as e:
            raise DownloadError(FALLBACK_MESSAGE, detail=str(e)) from e

        return [Reply.to(data).video_buffer(video_buffer, title)]

    @staticmethod
    def _match_error(error: str) -> str:
        for pattern, message in YTDLP_ERROR_MESSAGES.items():
            if pattern in error:
                return message
        return FALLBACK_MESSAGE
