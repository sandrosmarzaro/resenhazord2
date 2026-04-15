"""Live football matches from Transfermarkt."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    ParsedCommand,
    Platform,
)
from bot.domain.models.football import MatchStatus

if TYPE_CHECKING:
    from bot.domain.models.command_data import CommandData
    from bot.domain.models.message import BotMessage

from bot.domain.services.score_formatter import (
    apply_soft_cap as _apply_soft_cap,
    build_section,
    format_date_label as _format_date_label,
    format_finished_row,
    format_live_row,
    format_upcoming_row,
    is_within_upcoming_window,
    score_emoji as _score_emoji,
)
from bot.domain.services.score_formatter import _get_current_datetime
from bot.domain.services.score_formatter import _get_current_date
from bot.domain.services.transfermarkt.service import TransfermarktService
from bot.data.number_emoji import NUMBER_EMOJI, MAX_EMOJI_SCORE


class ScoreCommand(Command):
    _upcoming_window_hours: ClassVar[int] = 6
    _section_soft_cap: ClassVar[int] = 7

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='placar',
            aliases=['score'],
            flags=['past', 'now', 'next'],
            category=Category.OTHER,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Jogos de futebol ao vivo.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        matches = await TransfermarktService.fetch_live_matches()

        show_past = 'past' in parsed.flags
        show_now = 'now' in parsed.flags
        show_next = 'next' in parsed.flags
        if not (show_past or show_now or show_next):
            show_past = show_now = show_next = True

        live_all = [m for m in matches if m.status == MatchStatus.LIVE] if show_now else []
        window_hours = ScoreCommand._upcoming_window_hours
        upcoming_all = (
            [
                m
                for m in matches
                if m.status == MatchStatus.NOT_STARTED
                and is_within_upcoming_window(m.match_time, window_hours)
            ]
            if show_next
            else []
        )
        finished_all = [m for m in matches if m.status == MatchStatus.FINISHED] if show_past else []

        soft_cap = ScoreCommand._section_soft_cap
        live_matches = _apply_soft_cap(live_all, soft_cap)
        upcoming_matches = _apply_soft_cap(upcoming_all, soft_cap)
        finished_matches = _apply_soft_cap(finished_all, soft_cap)

        if not live_matches and not upcoming_matches and not finished_matches:
            return [Reply.to(data).text('Nenhum jogo ao vivo agora. ✨')]

        lines: list[str] = []
        if live_matches:
            lines.extend(build_section('🔥 *Ao Vivo*\n', live_matches, format_live_row))
        if upcoming_matches:
            lines.extend(build_section('📅 *Próximos*\n', upcoming_matches, format_upcoming_row))
        if finished_matches:
            lines.extend(build_section('✅ *Encerrados*\n', finished_matches, format_finished_row))

        reply = Reply.to(data).text('\n'.join(lines))
        reply.quotes_message_id = data.reply_to_message_id
        return [reply]
