import base64

from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent

THUMBNAIL = b'\xff\xd8jpeg'


class TestVideoThumbnail:
    def test_url_video_carries_the_thumbnail_as_base64(self):
        content = VideoContent(url='https://x/v.mp4', jpeg_thumbnail=THUMBNAIL)

        assert content.to_dict()['jpeg_thumbnail'] == base64.b64encode(THUMBNAIL).decode()

    def test_url_video_without_a_thumbnail_leaves_the_key_out(self):
        content = VideoContent(url='https://x/v.mp4')

        assert 'jpeg_thumbnail' not in content.to_dict()

    def test_buffer_video_carries_the_thumbnail_as_base64(self):
        content = VideoBufferContent(data=b'mp4', jpeg_thumbnail=THUMBNAIL)

        assert content.to_dict()['jpeg_thumbnail'] == base64.b64encode(THUMBNAIL).decode()

    def test_buffer_video_without_a_thumbnail_leaves_the_key_out(self):
        content = VideoBufferContent(data=b'mp4')

        assert 'jpeg_thumbnail' not in content.to_dict()
