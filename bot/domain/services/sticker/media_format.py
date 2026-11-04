from typing import ClassVar


class MediaFormat:
    MIN_VIDEO_SIGNATURE_LEN: ClassVar[int] = 12
    MIN_ANIMATED_WEBP_LEN: ClassVar[int] = 21
    WEBP_ANIMATION_FLAG: ClassVar[int] = 0x02
    DEFAULT_FRAME_DURATION_MS: ClassVar[int] = 100
    ANMF_DURATION_OFFSET: ClassVar[int] = 12
    ANMF_DURATION_SIZE: ClassVar[int] = 3

    @classmethod
    def is_video(cls, buffer: bytes) -> bool:
        if len(buffer) < cls.MIN_VIDEO_SIGNATURE_LEN:
            return False
        # MP4/MOV: ftyp box at offset 4
        if buffer[4:8] == b'ftyp':
            return True
        # AVI
        if buffer[:4] == b'RIFF' and buffer[8:12] == b'AVI ':
            return True
        # MKV/WebM
        return buffer[:4] == b'\x1a\x45\xdf\xa3'

    @classmethod
    def is_animated_webp(cls, buffer: bytes) -> bool:
        if len(buffer) < cls.MIN_ANIMATED_WEBP_LEN:
            return False
        if buffer[:4] != b'RIFF' or buffer[8:12] != b'WEBP':
            return False
        if buffer[12:16] != b'VP8X':
            return False
        return bool(buffer[20] & cls.WEBP_ANIMATION_FLAG)

    @classmethod
    def frame_durations(cls, buffer: bytes, n_frames: int) -> list[int]:
        # PIL's WEBP reader does not surface per-frame durations reliably
        # (returns None/0 for many inputs), so read them straight from ANMF
        # chunks in the RIFF container.
        durations: list[int] = []
        header_size = 8
        pos = 12
        while pos + header_size <= len(buffer):
            fourcc = buffer[pos : pos + 4]
            chunk_size = int.from_bytes(buffer[pos + 4 : pos + header_size], 'little')
            if fourcc == b'ANMF':
                start = pos + header_size + cls.ANMF_DURATION_OFFSET
                end = start + cls.ANMF_DURATION_SIZE
                if end <= len(buffer):
                    raw = int.from_bytes(buffer[start:end], 'little')
                    durations.append(raw or cls.DEFAULT_FRAME_DURATION_MS)
            pos += header_size + chunk_size + (chunk_size & 1)
        while len(durations) < n_frames:
            durations.append(cls.DEFAULT_FRAME_DURATION_MS)
        return durations[:n_frames]
