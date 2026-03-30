from dataclasses import dataclass

import discord
import structlog

from bot.adapters.discord.music.embeds import MusicEmbedBuilder
from bot.adapters.discord.music.queue import LoopMode
from bot.adapters.discord.music.voice_manager import VoiceManager
from bot.data.music_player import LOOP_MODE_EMOJIS, LOOP_MODE_LABELS
from bot.domain.models.track import Track
from bot.domain.services.ytdlp_audio import YtDlpAudioService

logger = structlog.get_logger()

NUMBER_EMOJIS = ['1️⃣', '2️⃣', '3️⃣']
SEARCH_TIMEOUT_SECONDS = 60


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

    @discord.ui.button(emoji='🔀', label='Shuffle', style=discord.ButtonStyle.secondary, row=1)
    async def shuffle_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        queue.shuffle()
        await interaction.response.send_message('Fila embaralhada.', ephemeral=True)

    @discord.ui.button(emoji='📋', label='Fila', style=discord.ButtonStyle.secondary, row=1)
    async def queue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        if queue.is_empty:
            await interaction.response.send_message('A fila esta vazia.', ephemeral=True)
            return

        embed = MusicEmbedBuilder.queue_list(queue)
        view = QueueView(self._voice_manager, self._guild_id)
        view.refresh_select_options()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@dataclass(frozen=True)
class SearchContext:
    voice_manager: VoiceManager
    guild_id: int
    voice_channel: discord.VoiceChannel | discord.StageChannel
    text_channel: discord.abc.Messageable
    requester_name: str
    requester_id: int


class SearchResultView(discord.ui.View):
    def __init__(self, tracks: list[Track], ctx: SearchContext) -> None:
        super().__init__(timeout=SEARCH_TIMEOUT_SECONDS)
        self._tracks = tracks
        self._ctx = ctx

        for i, track in enumerate(tracks):
            self.add_item(
                SearchSelectButton(
                    index=i,
                    track=track,
                    view_ref=self,
                )
            )
        self.add_item(SearchCancelButton())

    async def on_timeout(self) -> None:
        self.stop()

    async def select_track(self, interaction: discord.Interaction, index: int) -> None:
        track = self._tracks[index]
        ctx = self._ctx

        await interaction.response.defer()

        resolved = await YtDlpAudioService.resolve_stream(
            track.url,
            requested_by=ctx.requester_name,
            requested_by_id=ctx.requester_id,
        )

        queue = ctx.voice_manager.get_queue(ctx.guild_id)
        position = queue.add(resolved)

        await ctx.voice_manager.ensure_connected(ctx.voice_channel)
        ctx.voice_manager.set_text_channel(ctx.guild_id, ctx.text_channel)

        if not ctx.voice_manager.is_playing(ctx.guild_id):
            await ctx.voice_manager.play_track(ctx.guild_id, resolved)
            await interaction.followup.send(
                f'Tocando agora: **{resolved.title}**',
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f'Adicionado na fila (#{position + 1}): **{resolved.title}**',
                ephemeral=True,
            )

        self.stop()


class SearchSelectButton(discord.ui.Button):
    def __init__(self, index: int, track: Track, view_ref: SearchResultView) -> None:
        minutes, seconds = divmod(track.duration, 60)
        super().__init__(
            emoji=NUMBER_EMOJIS[index],
            label=f'{track.title[:40]} ({minutes}:{seconds:02d})',
            style=discord.ButtonStyle.primary,
        )
        self._index = index
        self._view_ref = view_ref

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._view_ref.select_track(interaction, self._index)


class SearchCancelButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label='Cancelar',
            emoji='❌',
            style=discord.ButtonStyle.secondary,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(
            content='Busca cancelada.',
            embed=None,
            view=None,
        )
        self.view.stop()


QUEUE_TIMEOUT_SECONDS = 120
TRACKS_PER_PAGE = 10


class QueueView(discord.ui.View):
    def __init__(self, voice_manager: VoiceManager, guild_id: int, page: int = 0) -> None:
        super().__init__(timeout=QUEUE_TIMEOUT_SECONDS)
        self._voice_manager = voice_manager
        self._guild_id = guild_id
        self._page = page
        self._update_buttons()

    def _update_buttons(self) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        total_pages = max(1, (queue.size + TRACKS_PER_PAGE - 1) // TRACKS_PER_PAGE)
        self.prev_page_button.disabled = self._page <= 0
        self.next_page_button.disabled = self._page >= total_pages - 1

    @discord.ui.button(emoji='◀', style=discord.ButtonStyle.secondary)
    async def prev_page_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        self._page = max(0, self._page - 1)
        self._update_buttons()
        queue = self._voice_manager.get_queue(self._guild_id)
        embed = MusicEmbedBuilder.queue_list(queue, self._page, TRACKS_PER_PAGE)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji='▶', style=discord.ButtonStyle.secondary)
    async def next_page_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        total_pages = max(1, (queue.size + TRACKS_PER_PAGE - 1) // TRACKS_PER_PAGE)
        self._page = min(total_pages - 1, self._page + 1)
        self._update_buttons()
        embed = MusicEmbedBuilder.queue_list(queue, self._page, TRACKS_PER_PAGE)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(placeholder='Selecione uma musica para gerenciar...')
    async def track_select(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select,
    ) -> None:
        index = int(select.values[0])
        view = TrackActionView(self._voice_manager, self._guild_id, index, parent=self)
        queue = self._voice_manager.get_queue(self._guild_id)
        tracks = queue.tracks
        if index < len(tracks):
            track = tracks[index]
            await interaction.response.send_message(
                f'Gerenciar: **{track.title}**',
                view=view,
                ephemeral=True,
            )

    def refresh_select_options(self) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        start = self._page * TRACKS_PER_PAGE
        end = min(start + TRACKS_PER_PAGE, queue.size)
        options: list[discord.SelectOption] = []
        for i in range(start, end):
            track = queue.tracks[i]
            label = f'{i + 1}. {track.title[:95]}'
            options.append(discord.SelectOption(label=label, value=str(i)))
        self.track_select.options = options or [
            discord.SelectOption(label='Fila vazia', value='-1'),
        ]

    async def on_timeout(self) -> None:
        self.stop()


TRACK_ACTION_TIMEOUT_SECONDS = 30


class TrackActionView(discord.ui.View):
    def __init__(
        self,
        voice_manager: VoiceManager,
        guild_id: int,
        track_index: int,
        parent: QueueView,
    ) -> None:
        super().__init__(timeout=TRACK_ACTION_TIMEOUT_SECONDS)
        self._voice_manager = voice_manager
        self._guild_id = guild_id
        self._track_index = track_index
        self._parent = parent

    async def _refresh_parent(self, interaction: discord.Interaction) -> None:
        self._parent.refresh_select_options()
        self._parent._update_buttons()
        queue = self._voice_manager.get_queue(self._guild_id)
        embed = MusicEmbedBuilder.queue_list(queue, self._parent._page, TRACKS_PER_PAGE)
        msg = getattr(self._parent, 'message', None)
        if msg:
            await msg.edit(embed=embed, view=self._parent)

    @discord.ui.button(label='Remover', emoji='🗑️', style=discord.ButtonStyle.danger)
    async def remove_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        removed = queue.remove(self._track_index)
        if removed:
            await interaction.response.edit_message(
                content=f'Removido: **{removed.title}**',
                view=None,
            )
        else:
            await interaction.response.edit_message(content='Musica nao encontrada.', view=None)
        await self._refresh_parent(interaction)
        self.stop()

    @discord.ui.button(label='Mover pro topo', emoji='⬆️', style=discord.ButtonStyle.primary)
    async def move_top_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        moved = queue.move_to_top(self._track_index)
        if moved:
            track = queue.tracks[queue.current_index + 1]
            await interaction.response.edit_message(
                content=f'Movido pro topo: **{track.title}**',
                view=None,
            )
        else:
            await interaction.response.edit_message(
                content='Nao foi possivel mover.',
                view=None,
            )
        await self._refresh_parent(interaction)
        self.stop()

    @discord.ui.button(label='Mover pro final', emoji='⬇️', style=discord.ButtonStyle.primary)
    async def move_bottom_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        queue = self._voice_manager.get_queue(self._guild_id)
        moved = queue.move_to_bottom(self._track_index)
        if moved:
            await interaction.response.edit_message(
                content='Movido pro final da fila.',
                view=None,
            )
        else:
            await interaction.response.edit_message(
                content='Nao foi possivel mover.',
                view=None,
            )
        await self._refresh_parent(interaction)
        self.stop()
