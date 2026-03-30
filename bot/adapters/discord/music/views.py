import discord
import structlog

from bot.adapters.discord.music.embeds import MusicEmbedBuilder
from bot.adapters.discord.music.queue import LoopMode
from bot.adapters.discord.music.voice_manager import VoiceManager
from bot.data.music_player import LOOP_MODE_EMOJIS, LOOP_MODE_LABELS
from bot.domain.services.ytdlp_audio import YtDlpAudioService

logger = structlog.get_logger()


class NowPlayingView(discord.ui.View):
    def __init__(self, voice_manager: VoiceManager, guild_id: int) -> None:
        super().__init__(timeout=None)
        self._voice_manager = voice_manager
        self._guild_id = guild_id

    async def _refresh_embed(self, interaction: discord.Interaction) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        track = queue.current
        if not track:
            return

        embed = MusicEmbedBuilder.now_playing(track, queue)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji='⏮', style=discord.ButtonStyle.secondary, row=0)
    async def back_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        track = queue.back()
        if not track:
            await interaction.response.send_message(
                'Nao ha musica anterior.',
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        track = await YtDlpAudioService.resolve_stream(
            track.url,
            requested_by=track.requested_by,
            requested_by_id=track.requested_by_id,
        )
        await self._voice_manager.play_track(self._guild_id, track)

    @discord.ui.button(emoji='⏸', label='Pausar', style=discord.ButtonStyle.primary, row=0)
    async def pause_resume_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        vc = self._voice_manager.get_voice_client(self._guild_id)
        if not vc:
            return

        if vc.is_paused():
            vc.resume()
            button.emoji = '⏸'
            button.label = 'Pausar'
        else:
            vc.pause()
            button.emoji = '▶'
            button.label = 'Retomar'

        await self._refresh_embed(interaction)

    @discord.ui.button(emoji='⏹', label='Parar', style=discord.ButtonStyle.danger, row=0)
    async def stop_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self._voice_manager.stop(self._guild_id)
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(emoji='⏭', style=discord.ButtonStyle.secondary, row=0)
    async def skip_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self._voice_manager.skip(self._guild_id)
        await interaction.response.send_message('Musica pulada.', ephemeral=True)

    @discord.ui.button(emoji='🔉', style=discord.ButtonStyle.secondary, row=1)
    async def volume_down_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        new_vol = queue.volume_down()

        vc = self._voice_manager.get_voice_client(self._guild_id)
        if vc and vc.source and hasattr(vc.source, 'volume'):
            vc.source.volume = new_vol

        await self._refresh_embed(interaction)

    @discord.ui.button(emoji='🔊', style=discord.ButtonStyle.secondary, row=1)
    async def volume_up_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        new_vol = queue.volume_up()

        vc = self._voice_manager.get_voice_client(self._guild_id)
        if vc and vc.source and hasattr(vc.source, 'volume'):
            vc.source.volume = new_vol

        await self._refresh_embed(interaction)

    @discord.ui.button(emoji='🔁', label='Repetir', style=discord.ButtonStyle.secondary, row=1)
    async def loop_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        new_mode = queue.cycle_loop()
        button.emoji = LOOP_MODE_EMOJIS[new_mode]
        button.label = f'Repetir: {LOOP_MODE_LABELS[new_mode]}'

        if new_mode == LoopMode.OFF:
            button.style = discord.ButtonStyle.secondary
        else:
            button.style = discord.ButtonStyle.success

        await self._refresh_embed(interaction)

    @discord.ui.button(emoji='📋', label='Fila', style=discord.ButtonStyle.secondary, row=1)
    async def queue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        embed = MusicEmbedBuilder.queue_list(queue)
        await interaction.response.send_message(embed=embed, ephemeral=True)
