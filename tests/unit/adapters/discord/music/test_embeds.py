from bot.adapters.discord.music.embeds import MusicEmbedBuilder
from bot.adapters.discord.music.queue import MusicQueue
from bot.data.music_player import EMBED_COLOR
from bot.domain.models.track import Track


def _track(title: str = 'Song', index: int = 0) -> Track:
    return Track(
        title=f'{title} {index}',
        author='Artist',
        url=f'https://youtube.com/watch?v={index}',
        stream_url=f'https://stream/{index}',
        duration=245,
        thumbnail=f'https://thumb/{index}.jpg',
        requested_by='User',
        requested_by_id=1,
    )


class TestNowPlaying:
    def test_has_title_and_author(self):
        queue = MusicQueue()
        track = _track()
        queue.add(track)

        embed = MusicEmbedBuilder.now_playing(track, queue)

        assert embed.title == 'Song 0'
        assert '**Artist**' in embed.description
        assert embed.color.value == EMBED_COLOR

    def test_has_duration_field(self):
        queue = MusicQueue()
        track = _track()
        queue.add(track)

        embed = MusicEmbedBuilder.now_playing(track, queue)

        duration_field = next(f for f in embed.fields if f.name == 'Duracao')
        assert duration_field.value == '4:05'

    def test_has_volume_field(self):
        queue = MusicQueue()
        track = _track()
        queue.add(track)

        embed = MusicEmbedBuilder.now_playing(track, queue)

        volume_field = next(f for f in embed.fields if f.name == 'Volume')
        assert volume_field.value == '50%'

    def test_has_loop_field(self):
        queue = MusicQueue()
        track = _track()
        queue.add(track)

        embed = MusicEmbedBuilder.now_playing(track, queue)

        loop_field = next(f for f in embed.fields if f.name == 'Repetir')
        assert 'Desativado' in loop_field.value

    def test_loop_track_mode_shown(self):
        queue = MusicQueue()
        track = _track()
        queue.add(track)
        queue.cycle_loop()

        embed = MusicEmbedBuilder.now_playing(track, queue)

        loop_field = next(f for f in embed.fields if f.name == 'Repetir')
        assert 'Musica' in loop_field.value

    def test_has_footer_with_requester(self):
        queue = MusicQueue()
        track = _track()
        queue.add(track)

        embed = MusicEmbedBuilder.now_playing(track, queue)

        assert 'User' in embed.footer.text
        assert '1/1' in embed.footer.text

    def test_has_thumbnail(self):
        queue = MusicQueue()
        track = _track()
        queue.add(track)

        embed = MusicEmbedBuilder.now_playing(track, queue)

        assert embed.thumbnail.url == track.thumbnail


class TestQueueList:
    def test_empty_queue(self):
        queue = MusicQueue()

        embed = MusicEmbedBuilder.queue_list(queue)

        assert 'vazia' in embed.description

    def test_shows_tracks(self):
        queue = MusicQueue()
        for i in range(3):
            queue.add(_track(index=i))

        embed = MusicEmbedBuilder.queue_list(queue)

        assert 'Song 0' in embed.description
        assert 'Song 1' in embed.description
        assert 'Song 2' in embed.description

    def test_marks_current_track(self):
        queue = MusicQueue()
        for i in range(3):
            queue.add(_track(index=i))

        embed = MusicEmbedBuilder.queue_list(queue)

        assert '▶ Song 0' in embed.description

    def test_pagination(self):
        queue = MusicQueue()
        for i in range(15):
            queue.add(_track(index=i))

        embed = MusicEmbedBuilder.queue_list(queue, page=1, tracks_per_page=10)

        assert 'Song 10' in embed.description
        assert 'Song 0' not in embed.description
        assert '2/2' in embed.footer.text


class TestSearchResults:
    def test_shows_numbered_results(self):
        tracks = [_track(index=i) for i in range(3)]

        embed = MusicEmbedBuilder.search_results(tracks)

        assert '**1.**' in embed.description
        assert '**2.**' in embed.description
        assert '**3.**' in embed.description
        assert 'Song 0' in embed.description
