import discord

from bot.adapters.discord.music.queue import MusicQueue
from bot.data.music_player import EMBED_COLOR, LOOP_MODE_EMOJIS, LOOP_MODE_LABELS
from bot.domain.models.track import Track


class MusicEmbedBuilder:
    @staticmethod
    def now_playing(track: Track, queue: MusicQueue) -> discord.Embed:
        minutes, seconds = divmod(track.duration, 60)
        duration_str = f'{minutes}:{seconds:02d}'

        loop_label = LOOP_MODE_LABELS[queue.loop_mode]
        loop_emoji = LOOP_MODE_EMOJIS[queue.loop_mode]
        volume_pct = int(queue.volume * 100)

        embed = discord.Embed(
            title=track.title,
            url=track.url,
            description=f'**{track.author}**',
            color=EMBED_COLOR,
        )

        if track.thumbnail and track.thumbnail.startswith('http'):
            embed.set_thumbnail(url=track.thumbnail)

        embed.add_field(name='Duracao', value=duration_str, inline=True)
        embed.add_field(name='Volume', value=f'{volume_pct}%', inline=True)
        embed.add_field(
            name='Repetir',
            value=f'{loop_emoji} {loop_label}',
            inline=True,
        )

        position = queue.current_index + 1
        total = queue.size
        embed.set_footer(text=f'Pedido por {track.requested_by}   |   {position}/{total} na fila')

        return embed

    @staticmethod
    def queue_list(queue: MusicQueue, page: int = 0, tracks_per_page: int = 10) -> discord.Embed:
        tracks = queue.tracks
        total = len(tracks)

        if total == 0:
            return discord.Embed(
                title='Fila de musicas',
                description='A fila esta vazia.',
                color=EMBED_COLOR,
            )

        start = page * tracks_per_page
        end = min(start + tracks_per_page, total)
        page_tracks = tracks[start:end]
        total_pages = (total + tracks_per_page - 1) // tracks_per_page

        lines: list[str] = []
        for i, track in enumerate(page_tracks, start=start + 1):
            prefix = '▶ ' if i - 1 == queue.current_index else ''
            minutes, seconds = divmod(track.duration, 60)
            lines.append(
                f'**{i}.** {prefix}{track.title} - {track.author} ({minutes}:{seconds:02d})'
            )

        embed = discord.Embed(
            title='Fila de musicas',
            description='\n'.join(lines),
            color=EMBED_COLOR,
        )
        embed.set_footer(text=f'Pagina {page + 1}/{total_pages}   |   {total} musicas na fila')

        return embed

    @staticmethod
    def search_results(tracks: list[Track]) -> discord.Embed:
        lines: list[str] = []
        for i, track in enumerate(tracks, start=1):
            minutes, seconds = divmod(track.duration, 60)
            lines.append(
                f'**{i}.** [{track.title}]({track.url})\n{track.author} ({minutes}:{seconds:02d})'
            )

        embed = discord.Embed(
            title='Resultados da busca',
            description='\n\n'.join(lines),
            color=EMBED_COLOR,
        )

        first_thumb = next((t.thumbnail for t in tracks if t.thumbnail), None)
        if first_thumb and first_thumb.startswith('http'):
            embed.set_thumbnail(url=first_thumb)

        return embed
