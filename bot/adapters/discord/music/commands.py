import re
from typing import ClassVar

import discord
import structlog
from discord import app_commands

from bot.adapters.discord.music.voice_manager import VoiceManager
from bot.data.music_errors import NO_PREVIOUS_TRACK, NO_VOICE_CHANNEL, NOT_PLAYING
from bot.domain.exceptions import ExternalServiceError, MusicError
from bot.domain.services.ytdlp_audio import YtDlpAudioService

logger = structlog.get_logger()


class MusicCommands:
    URL_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'https?://')

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

    def _register_play(self) -> None:
        vm = self._voice_manager

        @self._tree.command(name='play', description='Tocar uma musica', guild=self._guild)
        @app_commands.describe(query='URL ou termo de busca')
        async def play(interaction: discord.Interaction, query: str) -> None:
            guild = interaction.guild
            if not guild:
                return

            voice_state = getattr(interaction.user, 'voice', None)
            if not voice_state or not voice_state.channel:
                await interaction.response.send_message(NO_VOICE_CHANNEL, ephemeral=True)
                return

            await interaction.response.defer()

            try:
                is_url = self.URL_PATTERN.match(query) is not None

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
                        await interaction.followup.send('Nenhum resultado encontrado.')
                        return
                    track = await YtDlpAudioService.resolve_stream(
                        results[0].url,
                        requested_by=interaction.user.display_name,
                        requested_by_id=interaction.user.id,
                    )

                queue = vm.get_queue(guild.id)
                position = queue.add(track)

                await vm.ensure_connected(voice_state.channel)
                vm.set_text_channel(guild.id, interaction.channel)

                if not vm.is_playing(guild.id):
                    await vm.play_track(guild.id, track)
                    await interaction.followup.send(
                        f'Tocando agora: **{track.title}**',
                        silent=True,
                    )
                else:
                    await interaction.followup.send(
                        f'Adicionado na fila (#{position + 1}): **{track.title}** - {track.author}'
                    )
            except ExternalServiceError as e:
                await interaction.followup.send(e.user_message)
            except MusicError as e:
                await interaction.followup.send(e.user_message)

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
