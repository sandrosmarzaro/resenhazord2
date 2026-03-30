import asyncio
from typing import ClassVar

import discord
import structlog

from bot.adapters.discord.music.queue import MusicQueue
from bot.domain.models.track import Track

logger = structlog.get_logger()


class VoiceManager:
    IDLE_DISCONNECT_SECONDS: ClassVar[int] = 300
    FFMPEG_BEFORE_OPTIONS: ClassVar[str] = (
        '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    )
    FFMPEG_OPTIONS: ClassVar[str] = '-vn'

    def __init__(self) -> None:
        self._voice_clients: dict[int, discord.VoiceClient] = {}
        self._queues: dict[int, MusicQueue] = {}
        self._text_channels: dict[int, discord.abc.Messageable] = {}
        self._now_playing_messages: dict[int, discord.Message] = {}
        self._disconnect_tasks: dict[int, asyncio.Task[None]] = {}

    def get_queue(self, guild_id: int) -> MusicQueue:
        if guild_id not in self._queues:
            self._queues[guild_id] = MusicQueue()
        return self._queues[guild_id]

    def get_voice_client(self, guild_id: int) -> discord.VoiceClient | None:
        return self._voice_clients.get(guild_id)

    def get_now_playing_message(self, guild_id: int) -> discord.Message | None:
        return self._now_playing_messages.get(guild_id)

    def set_now_playing_message(self, guild_id: int, message: discord.Message) -> None:
        self._now_playing_messages[guild_id] = message

    def set_text_channel(self, guild_id: int, channel: discord.abc.Messageable) -> None:
        self._text_channels[guild_id] = channel

    async def ensure_connected(
        self,
        channel: discord.VoiceChannel | discord.StageChannel,
    ) -> discord.VoiceClient:
        guild_id = channel.guild.id
        self._cancel_disconnect_timer(guild_id)

        existing = self._voice_clients.get(guild_id)
        if existing and existing.is_connected():
            if existing.channel and existing.channel.id != channel.id:
                await existing.move_to(channel)
            return existing

        voice_client = await channel.connect()
        self._voice_clients[guild_id] = voice_client
        logger.info('voice_connected', guild_id=guild_id, channel=channel.name)
        return voice_client

    async def play_track(self, guild_id: int, track: Track) -> None:
        voice_client = self._voice_clients.get(guild_id)
        if not voice_client or not voice_client.is_connected():
            return

        self._cancel_disconnect_timer(guild_id)

        if voice_client.is_playing():
            voice_client.stop()

        queue = self.get_queue(guild_id)
        source = discord.FFmpegOpusAudio(
            track.stream_url,
            before_options=self.FFMPEG_BEFORE_OPTIONS,
            options=self.FFMPEG_OPTIONS,
        )
        volume_source = discord.PCMVolumeTransformer(source, volume=queue.volume)

        loop = asyncio.get_running_loop()

        def after_callback(error: Exception | None) -> None:
            if error:
                logger.error('playback_error', guild_id=guild_id, error=str(error))
            loop.call_soon_threadsafe(asyncio.ensure_future, self._on_track_end(guild_id, error))

        voice_client.play(volume_source, after=after_callback)
        logger.info('playback_started', guild_id=guild_id, title=track.title)

    async def stop(self, guild_id: int) -> None:
        queue = self.get_queue(guild_id)
        queue.clear()

        voice_client = self._voice_clients.get(guild_id)
        if voice_client and voice_client.is_playing():
            voice_client.stop()

        await self.disconnect(guild_id)

    async def skip(self, guild_id: int) -> Track | None:
        voice_client = self._voice_clients.get(guild_id)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
        return self.get_queue(guild_id).current

    async def disconnect(self, guild_id: int) -> None:
        self._cancel_disconnect_timer(guild_id)

        voice_client = self._voice_clients.pop(guild_id, None)
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            logger.info('voice_disconnected', guild_id=guild_id)

        self._queues.pop(guild_id, None)
        self._text_channels.pop(guild_id, None)
        self._now_playing_messages.pop(guild_id, None)

    def is_playing(self, guild_id: int) -> bool:
        vc = self._voice_clients.get(guild_id)
        return vc is not None and vc.is_playing()

    def is_connected(self, guild_id: int) -> bool:
        vc = self._voice_clients.get(guild_id)
        return vc is not None and vc.is_connected()

    async def _on_track_end(self, guild_id: int, error: Exception | None) -> None:
        queue = self.get_queue(guild_id)
        next_track = queue.advance()

        if next_track is None:
            self._schedule_disconnect_timer(guild_id)
            return

        await self.play_track(guild_id, next_track)

    def _schedule_disconnect_timer(self, guild_id: int) -> None:
        self._cancel_disconnect_timer(guild_id)
        self._disconnect_tasks[guild_id] = asyncio.create_task(self._idle_disconnect(guild_id))

    def _cancel_disconnect_timer(self, guild_id: int) -> None:
        task = self._disconnect_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()

    async def _idle_disconnect(self, guild_id: int) -> None:
        await asyncio.sleep(self.IDLE_DISCONNECT_SECONDS)
        logger.info('idle_disconnect', guild_id=guild_id)
        await self.disconnect(guild_id)
