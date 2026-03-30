import random
import re
from typing import ClassVar

import discord
import structlog
from discord import app_commands

from bot.adapters.discord.music.embeds import MusicEmbedBuilder
from bot.adapters.discord.music.views import QueueView, SearchContext, SearchResultView
from bot.adapters.discord.music.voice_manager import VoiceManager
from bot.data.music_errors import (
    NO_PREVIOUS_TRACK,
    NO_RESULTS,
    NO_VOICE_CHANNEL,
    NOT_PLAYING,
    PLAYLIST_EMPTY,
    QUEUE_EMPTY,
)
from bot.domain.exceptions import ExternalServiceError, MusicError
from bot.domain.services.ytdlp_audio import YtDlpAudioService

logger = structlog.get_logger()


class MusicCommands:
    URL_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'https?://')
    PLAYLIST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r'https?://.*(?:list=|/playlist/|/sets/)',
    )

    def __init__(
        self,
        tree: app_commands.CommandTree,
        guild: discord.Object,
        voice_manager: VoiceManager,
    ) -> None:
        self._tree = tree
        self._guild = guild
        self._voice_manager = voice_manager

    def register(self) -> None:
        self._register_play()
        self._register_skip()
        self._register_stop()
        self._register_back()
        self._register_np()
        self._register_queue()

    def _register_play(self) -> None:
        vm = self._voice_manager

        @self._tree.command(name='play', description='Tocar uma musica', guild=self._guild)
        @app_commands.describe(
            query='URL ou termo de busca',
            buscar='Mostrar opcoes de busca para escolher',
            shuffle='Embaralhar a playlist antes de tocar',
        )
        async def play(
            interaction: discord.Interaction,
            query: str,
            buscar: bool | None = None,  # noqa: FBT001
            shuffle: bool | None = None,  # noqa: FBT001
        ) -> None:
            guild = interaction.guild
            if not guild:
                return

            voice_state = getattr(interaction.user, 'voice', None)
            if not voice_state or not voice_state.channel:
                await interaction.response.send_message(NO_VOICE_CHANNEL, ephemeral=True)
                return

            is_url = self.URL_PATTERN.match(query) is not None

            ctx = SearchContext(
                voice_manager=vm,
                guild_id=guild.id,
                voice_channel=voice_state.channel,
                text_channel=interaction.channel,
                requester_name=interaction.user.display_name,
                requester_id=interaction.user.id,
            )

            if buscar and not is_url:
                await self._handle_search(interaction, query, ctx)
                return

            await interaction.response.defer()

            try:
                is_playlist = is_url and self.PLAYLIST_PATTERN.match(query) is not None
                if is_playlist:
                    await self._handle_playlist(interaction, query, ctx, shuffle=bool(shuffle))
                    return

                await self._handle_single_track(
                    interaction,
                    query,
                    is_url=is_url,
                    ctx=ctx,
                )
            except ExternalServiceError as e:
                await interaction.followup.send(e.user_message)
            except MusicError as e:
                await interaction.followup.send(e.user_message)

    @staticmethod
    async def _handle_single_track(
        interaction: discord.Interaction,
        query: str,
        *,
        is_url: bool,
        ctx: SearchContext,
    ) -> None:
        vm = ctx.voice_manager
        guild_id = ctx.guild_id
        voice_channel = ctx.voice_channel
        if is_url:
            track = await YtDlpAudioService.resolve_stream(
                query,
                requested_by=interaction.user.display_name,
                requested_by_id=interaction.user.id,
            )
        else:
            results = await YtDlpAudioService.search(
                query,
                limit=1,
                requested_by=interaction.user.display_name,
                requested_by_id=interaction.user.id,
            )
            if not results:
                await interaction.followup.send(NO_RESULTS)
                return
            track = await YtDlpAudioService.resolve_stream(
                results[0].url,
                requested_by=interaction.user.display_name,
                requested_by_id=interaction.user.id,
            )

        queue = vm.get_queue(guild_id)
        position = queue.add(track)

        await vm.ensure_connected(voice_channel)
        vm.set_text_channel(guild_id, interaction.channel)

        if not vm.is_playing(guild_id):
            await vm.play_track(guild_id, track)
            await interaction.followup.send(
                f'Tocando agora: **{track.title}**',
                silent=True,
            )
        else:
            await interaction.followup.send(
                f'Adicionado na fila (#{position + 1}): **{track.title}** - {track.author}'
            )

    @staticmethod
    async def _handle_search(
        interaction: discord.Interaction,
        query: str,
        ctx: SearchContext,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            results = await YtDlpAudioService.search(
                query,
                limit=3,
                requested_by=ctx.requester_name,
                requested_by_id=ctx.requester_id,
            )
        except ExternalServiceError as e:
            await interaction.followup.send(e.user_message, ephemeral=True)
            return

        if not results:
            await interaction.followup.send(NO_RESULTS, ephemeral=True)
            return

        embed = MusicEmbedBuilder.search_results(results)
        view = SearchResultView(tracks=results, ctx=ctx)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @staticmethod
    async def _handle_playlist(
        interaction: discord.Interaction,
        url: str,
        ctx: SearchContext,
        *,
        shuffle: bool = False,
    ) -> None:
        vm = ctx.voice_manager
        guild_id = ctx.guild_id

        try:
            tracks = await YtDlpAudioService.resolve_playlist(
                url,
                requested_by=ctx.requester_name,
                requested_by_id=ctx.requester_id,
            )
        except ExternalServiceError as e:
            await interaction.followup.send(e.user_message)
            return

        if not tracks:
            await interaction.followup.send(PLAYLIST_EMPTY)
            return

        if shuffle:
            random.shuffle(tracks)

        queue = vm.get_queue(guild_id)
        count = queue.add_many(tracks)

        await vm.ensure_connected(ctx.voice_channel)
        vm.set_text_channel(guild_id, ctx.text_channel)

        if not vm.is_playing(guild_id) and queue.current:
            first = queue.current
            resolved = await YtDlpAudioService.resolve_stream(
                first.url,
                requested_by=first.requested_by,
                requested_by_id=first.requested_by_id,
            )
            queue.replace_current(resolved)
            await vm.play_track(guild_id, resolved)

        suffix = ' (embaralhada)' if shuffle else ''
        await interaction.followup.send(f'{count} musicas adicionadas a fila.{suffix}')

    def _register_queue(self) -> None:
        vm = self._voice_manager

        @self._tree.command(
            name='queue',
            description='Mostrar a fila de musicas',
            guild=self._guild,
        )
        async def queue(interaction: discord.Interaction) -> None:
            guild = interaction.guild
            if not guild:
                return

            q = vm.get_queue(guild.id)
            if q.is_empty:
                await interaction.response.send_message(QUEUE_EMPTY, ephemeral=True)
                return

            embed = MusicEmbedBuilder.queue_list(q)
            view = QueueView(vm, guild.id)
            view.refresh_select_options()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    def _register_skip(self) -> None:
        vm = self._voice_manager

        @self._tree.command(name='skip', description='Pular a musica atual', guild=self._guild)
        async def skip(interaction: discord.Interaction) -> None:
            guild = interaction.guild
            if not guild:
                return

            if not vm.is_playing(guild.id):
                await interaction.response.send_message(NOT_PLAYING, ephemeral=True)
                return

            await vm.skip(guild.id)
            await interaction.response.send_message('Musica pulada.')

    def _register_stop(self) -> None:
        vm = self._voice_manager

        @self._tree.command(
            name='stop',
            description='Parar a musica e sair do canal',
            guild=self._guild,
        )
        async def stop(interaction: discord.Interaction) -> None:
            guild = interaction.guild
            if not guild:
                return

            if not vm.is_connected(guild.id):
                await interaction.response.send_message(NOT_PLAYING, ephemeral=True)
                return

            await vm.stop(guild.id)
            await interaction.response.send_message('Musica parada. Ate mais!')

    def _register_back(self) -> None:
        vm = self._voice_manager

        @self._tree.command(
            name='back',
            description='Voltar para a musica anterior',
            guild=self._guild,
        )
        async def back(interaction: discord.Interaction) -> None:
            guild = interaction.guild
            if not guild:
                return

            queue = vm.get_queue(guild.id)
            track = queue.back()
            if not track:
                await interaction.response.send_message(NO_PREVIOUS_TRACK, ephemeral=True)
                return

            await interaction.response.defer()
            track = await YtDlpAudioService.resolve_stream(
                track.url,
                requested_by=track.requested_by,
                requested_by_id=track.requested_by_id,
            )
            await vm.play_track(guild.id, track)
            await interaction.followup.send(f'Voltando: **{track.title}** - {track.author}')

    def _register_np(self) -> None:
        vm = self._voice_manager

        @self._tree.command(
            name='np',
            description='Mostrar a musica tocando agora',
            guild=self._guild,
        )
        async def np(interaction: discord.Interaction) -> None:
            guild = interaction.guild
            if not guild:
                return

            queue = vm.get_queue(guild.id)
            track = queue.current
            if not track:
                await interaction.response.send_message(NOT_PLAYING, ephemeral=True)
                return

            minutes, seconds = divmod(track.duration, 60)
            await interaction.response.send_message(
                f'Tocando agora: **{track.title}** - {track.author} ({minutes}:{seconds:02d})'
            )
