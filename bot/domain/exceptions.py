class BotError(Exception):
    """Base exception for all bot errors with a user-facing message."""

    def __init__(self, user_message: str, *, detail: str | None = None) -> None:
        self.user_message = user_message
        super().__init__(detail or user_message)


class CommandError(BotError):
    """Error during command execution that should show a user message."""


class MediaNotFoundError(CommandError):
    """No media attached when expected."""


class ValidationError(CommandError):
    """Invalid input (missing args, bad format)."""


class ExternalServiceError(CommandError):
    """External API failure."""


class DownloadError(ExternalServiceError):
    """yt-dlp or download failure."""
