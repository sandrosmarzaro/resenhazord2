"""League standings table from Transfermarkt."""

from bot.data.football import LEAGUE_CODES, LEAGUES, LeagueInfo
from bot.data.football_zones import (
    DEFAULT_ZONE_EMOJI,
    LEAGUE_ZONES,
    MEDAL_EMOJIS,
    ClassificationZone,
)
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    OptionDef,
    ParsedCommand,
    Platform,
)
from bot.domain.models.command_data import CommandData
from bot.domain.models.football import TmStandingRow
from bot.domain.models.message import BotMessage
from bot.domain.services.transfermarkt.service import TransfermarktService


class FootballStandingsCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='tabela',
            aliases=['table'],
            options=[OptionDef(name='liga', values=LEAGUE_CODES)],
            flags=['g4', 'z4'],
            category=Category.INFORMATION,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Tabela de classificação de uma liga de futebol com pontos, V/E/D e outros stats.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        liga_code = parsed.options.get('liga', 'br')
        league = LEAGUES[liga_code]
        standings = await TransfermarktService.fetch_full_standings(league)

        if not standings:
            return [Reply.to(data).text('Tabela nao encontrada. Tente novamente! ')]

        zones = LEAGUE_ZONES.get(liga_code, [])

        if 'g4' in parsed.flags and zones:
            standings = [r for r in standings if r.rank <= zones[0].end]
        elif 'z4' in parsed.flags and zones:
            standings = [r for r in standings if r.rank >= zones[-1].start]

        caption = self._format_table(standings, league, zones)
        return [Reply.to(data).text(caption)]

    @staticmethod
    def _format_table(
        standings: list[TmStandingRow],
        league: LeagueInfo,
        zones: list[ClassificationZone],
    ) -> str:
        lines: list[str] = [f'⚽ *{league.name}* {league.flag}']
        first_zone = _find_zone(standings[0].rank, zones) if standings else None
        prev_zone: ClassificationZone | None = first_zone
        is_first = True

        for row in standings:
            zone = _find_zone(row.rank, zones)

            if zone != prev_zone and not is_first:
                if zone is not None:
                    lines.append(f'\n── {zone.emoji} {zone.name} ──')
                else:
                    lines.append('')

            is_first = False
            prev_zone = zone
            emoji = MEDAL_EMOJIS.get(row.rank) or (zone.emoji if zone else DEFAULT_ZONE_EMOJI)
            diff = f'+{row.goal_diff}' if row.goal_diff > 0 else str(row.goal_diff)
            goals = f'{row.goals_for}:{row.goals_against}'
            lines.append(f'{emoji} {row.rank}. *{row.team}* — {row.points} pts')
            stats = f'    {row.matches}J  {row.wins}V  {row.draws}E  {row.losses}D  {goals}  {diff}'
            lines.append(stats)

        return '\n'.join(lines)


def _find_zone(rank: int, zones: list[ClassificationZone]) -> ClassificationZone | None:
    for zone in zones:
        if zone.start <= rank <= zone.end:
            return zone
    return None
