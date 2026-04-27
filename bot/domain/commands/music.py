import random

import structlog

from bot.data.deezer_genres import DEEZER_GENRES
from bot.data.music_genres import MUSIC_GENRES
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
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class MusicCommand(Command):
    DEEZER_CHART_URL = 'https://api.deezer.com/chart'
    JAMENDO_TRACKS_URL = 'https://api.jamendo.com/v3.0/tracks/'
    TRACK_LIMIT = 200
    JAMENDO_IMAGE_SIZE = 500

    def __init__(self, jamendo_client_id: str = '') -> None:
        super().__init__()
        self._jamendo_client_id = jamendo_client_id

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='música',
            aliases=['music'],
            flags=['free', Flag.SHOW, Flag.DM],
            args=ArgType.OPTIONAL,
            args_label='gênero',
            category=Category.DOWNLOAD,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return (
            'Receba um preview de música popular (Deezer)'
            ' ou use "free" para músicas completas gratuitas (Jamendo).'
        )

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            if 'free' in parsed.flags:
                return await self._run_jamendo(data, parsed)
            return await self._run_deezer(data, parsed)
        except Exception:
            logger.exception('music_command_error')
            return [Reply.to(data).text('Erro ao buscar música. Tente novamente mais tarde! 🎵')]

    async def _run_deezer(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        tag, genre_id = self._parse_deezer_genre(parsed.rest)

        res = await HttpClient.get(
            f'{self.DEEZER_CHART_URL}/{genre_id}/tracks',
            params={'limit': self.TRACK_LIMIT},
        )
        tracks = res.json().get('data') or []
        if not tracks:
            return [Reply.to(data).text('Não encontrei músicas para esse gênero. Tente outro! 🎵')]

        track = random.choice(tracks)  # noqa: S311
        duration = self._format_duration(track['duration'])
        caption = (
            f'🎵 *{track["title"]}*\n'
            f'👨\u200d🦱 _{track["artist"]["name"]}_\n'
            f'\n📚 {track["album"]["title"]}\n'
            f'🧬 {tag}\n'
            f'⏱️ {duration}'
        )

        return [
            Reply.to(data).image(track['album']['cover_medium'], caption),
            Reply.to(data).audio(track['preview']),
        ]

    async def _run_jamendo(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        genre = self._parse_jamendo_genre(parsed.rest)

        res = await HttpClient.get(
            self.JAMENDO_TRACKS_URL,
            params={
                'client_id': self._jamendo_client_id,
                'format': 'json',
                'limit': self.TRACK_LIMIT,
                'tags': genre,
                'order': 'popularity_total',
                'imagesize': self.JAMENDO_IMAGE_SIZE,
                'audioformat': 'mp32',
            },
        )
        tracks = res.json().get('results') or []
        if not tracks:
            return [Reply.to(data).text('Não encontrei músicas para esse gênero. Tente outro! 🎵')]

        track = random.choice(tracks)  # noqa: S311
        duration = self._format_duration(track['duration'])
        caption = (
            f'🎵 *{track["name"]}*\n'
            f'👨\u200d🦱 _{track["artist_name"]}_\n'
            f'\n📚 {track["album_name"]}\n'
            f'🧬 {genre}\n'
            f'⏱️ {duration}\n'
            f'📅 {track["releasedate"]}'
        )

        return [
            Reply.to(data).image(track['image'], caption),
            Reply.to(data).audio(track['audio']),
        ]

    @staticmethod
    def _parse_deezer_genre(rest: str) -> tuple[str, int]:
        cleaned = rest.strip().lower()
        if cleaned and cleaned in DEEZER_GENRES:
            return cleaned, DEEZER_GENRES[cleaned]
        return 'all', 0

    @staticmethod
    def _parse_jamendo_genre(rest: str) -> str:
        cleaned = rest.strip().lower()
        if cleaned and cleaned in MUSIC_GENRES:
            return cleaned
        return random.choice(MUSIC_GENRES)  # noqa: S311

    @staticmethod
    def _format_duration(seconds: int) -> str:
        mins = seconds // 60
        secs = seconds % 60
        return f'{mins}:{secs:02d}'
