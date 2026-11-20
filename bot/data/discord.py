BUFFER_EXTENSIONS: frozendict[str, str] = frozendict(
    {
        'image_buffer': 'png',
        'video_buffer': 'mp4',
        'audio_buffer': 'mp4',
        'audio_mp3': 'mp3',
    }
)

# Permissions the add-to-server link asks for: send messages (bit 11), embed links
# (bit 14), attach files (bit 15) and use application commands (bit 31).
INVITE_PERMISSIONS: int = (1 << 11) | (1 << 14) | (1 << 15) | (1 << 31)
