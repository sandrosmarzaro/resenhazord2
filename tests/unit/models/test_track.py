from bot.domain.models.track import Track


class TestTrack:
    def test_create(self):
        track = Track(
            title='Test Song',
            author='Test Artist',
            url='https://youtube.com/watch?v=abc',
            stream_url='https://rr.googlevideo.com/abc',
            duration=240,
            thumbnail='https://i.ytimg.com/vi/abc/hqdefault.jpg',
            requested_by='User',
            requested_by_id=123456,
        )

        assert track.title == 'Test Song'
        assert track.author == 'Test Artist'
        assert track.duration == 240
        assert track.requested_by_id == 123456

    def test_frozen(self):
        track = Track(
            title='Song',
            author='Artist',
            url='https://youtube.com/watch?v=abc',
            stream_url='https://rr.googlevideo.com/abc',
            duration=180,
            thumbnail='https://i.ytimg.com/vi/abc/hqdefault.jpg',
            requested_by='User',
            requested_by_id=1,
        )

        import pytest

        with pytest.raises(AttributeError):
            track.title = 'New Title'  # type: ignore[misc]
