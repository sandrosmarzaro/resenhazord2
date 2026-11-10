class BotError(Exception):
    """Base exception for all bot errors with a user-facing message."""

    def __init__(self, user_message: str, *, detail: str | None = None) -> None:
        self.user_message = user_message
        super().__init__(detail or user_message)


class CommandError(BotError):
    """Error during command execution that should show a user message."""


class MediaNotFoundError(CommandError):
    """No media attached when expected."""


class MediaUnavailableError(CommandError):
    """Media is attached but could not be downloaded."""


class ValidationError(CommandError):
    """Invalid input (missing args, bad format)."""


class ExternalServiceError(CommandError):
    """External API failure."""


class DownloadError(ExternalServiceError):
    """yt-dlp or download failure."""


class StickerTooLargeError(CommandError):
    """Sticker still over WhatsApp's animated-sticker limit after dropping frames."""

    def __init__(self) -> None:
        super().__init__(
            'Esse sticker passou do limite de 500 KB do WhatsApp. Tente uma mídia mais curta '
            'ou com menos qualidade, tipo ,stic quality 50! 😵'
        )


class VoiceNoteError(CommandError):
    """ffmpeg could not turn the audio into the opus voice note a status needs."""

    def __init__(self, detail: str) -> None:
        super().__init__('Não consegui converter esse áudio pro status do grupo! 😅', detail=detail)


class VideoRemuxError(CommandError):
    """ffmpeg could not rewrite the mp4 into one WhatsApp accepts."""

    def __init__(self, detail: str) -> None:
        super().__init__('Não consegui preparar esse vídeo, tenta de novo! 😅', detail=detail)
