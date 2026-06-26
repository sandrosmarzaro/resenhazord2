"""Live football matches from Transfermarkt."""

from typing import TYPE_CHECKING, ClassVar

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    ParsedCommand,
    Platform,
)
from bot.domain.models.football import MatchStatus, TmLiveMatch

if TYPE_CHECKING:
    from bot.domain.models.command_data import CommandData
    from bot.domain.models.message import BotMessage

from bot.domain.services.score_formatter import (
    apply_soft_cap,
    build_section,
    format_date_label,
    format_finished_row,
    format_live_row,
    format_upcoming_row,
    is_within_upcoming_window,
    score_emoji,
)
from bot.domain.services.transfermarkt.service import (
    TransfermarktService,
)

# Re-export for backward compatibility with tests
_apply_soft_cap = apply_soft_cap
_score_emoji = score_emoji
_format_date_label = format_date_label


class ScoreCommand(Command):
    _upcoming_window_hours: ClassVar[int] = 6
    _section_soft_cap: ClassVar[int] = 7

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='placar',
            aliases=['score'],
            flags=['past', 'now', 'next'],
            category=Category.INFORMATION,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Placar ao vivo de jogos de futebol com resultados ao vivo, próximos e encerrados.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        matches = await TransfermarktService.fetch_live_matches()
        show_past, show_now, show_next = self._resolve_flags(parsed)

        live = self._live_matches(matches) if show_now else []
        upcoming = self._upcoming_matches(matches) if show_next else []
        finished = self._finished_matches(matches) if show_past else []

        cap = ScoreCommand._section_soft_cap
        capped_live = _apply_soft_cap(live, cap)
        capped_upcoming = _apply_soft_cap(upcoming, cap)
        capped_finished = _apply_soft_cap(finished, cap)

        if not any((capped_live, capped_upcoming, capped_finished)):
            return [Reply.to(data).text('Nenhum jogo ao vivo agora. ✨')]

        lines = self._build_sections(capped_live, capped_upcoming, capped_finished)
        message = Reply.to(data).text('\n'.join(lines))
        message.quoted_message_id = data.quoted_message_id
        return [message]

    @staticmethod
    def _resolve_flags(parsed: ParsedCommand) -> tuple[bool, bool, bool]:
        show_past = 'past' in parsed.flags
        show_now = 'now' in parsed.flags
        show_next = 'next' in parsed.flags
        if not any((show_past, show_now, show_next)):
            show_past = show_now = show_next = True
        return show_past, show_now, show_next

    @staticmethod
    def _live_matches(matches: list[TmLiveMatch]) -> list[TmLiveMatch]:
        return [m for m in matches if m.status == MatchStatus.LIVE]

    @staticmethod
    def _upcoming_matches(matches: list[TmLiveMatch]) -> list[TmLiveMatch]:
        window = ScoreCommand._upcoming_window_hours
        return [
            m
            for m in matches
            if m.status == MatchStatus.NOT_STARTED
            and is_within_upcoming_window(m.match_time, window)
        ]

    @staticmethod
    def _finished_matches(matches: list[TmLiveMatch]) -> list[TmLiveMatch]:
        return [m for m in matches if m.status == MatchStatus.FINISHED]

    @staticmethod
    def _build_sections(
        live: list[TmLiveMatch],
        upcoming: list[TmLiveMatch],
        finished: list[TmLiveMatch],
    ) -> list[str]:
        lines: list[str] = []
        if live:
            lines.extend(build_section('🔥 *Ao Vivo*\n', live, format_live_row))
        if upcoming:
            lines.extend(build_section('📅 *Próximos Jogos*\n', upcoming, format_upcoming_row))
        if finished:
            lines.extend(build_section('✅ *Encerrados*\n', finished, format_finished_row))
        return lines
