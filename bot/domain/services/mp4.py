import re
from typing import ClassVar


class Mp4:
    SIGNATURE: ClassVar[bytes] = b'ftyp'
    SIGNATURE_OFFSET: ClassVar[slice] = slice(4, 8)
    # Every track has a `hdlr` box; an audio track's handler type is `soun`.
    SOUND_HANDLER: ClassVar[re.Pattern[bytes]] = re.compile(rb'hdlr.{8}soun', re.DOTALL)

    @classmethod
    def is_silent(cls, buffer: bytes) -> bool:
        is_mp4 = buffer[cls.SIGNATURE_OFFSET] == cls.SIGNATURE
        return is_mp4 and not cls.SOUND_HANDLER.search(buffer)
