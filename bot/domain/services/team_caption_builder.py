"""Build formatted team captions for bot responses."""

from bot.data.football import LeagueInfo
from bot.domain.models.football import SportsDBTeam, TmSquadStats


class TeamCaptionBuilder:
    @staticmethod
    def build(
        club: TmSquadStats,
        sports_team: SportsDBTeam | None,
        league: LeagueInfo,
        rank: int | None,
        global_rank: int | None = None,
    ) -> str:
        country = sports_team.country if sports_team else league.country
        founded = sports_team.founded if sports_team else ''
        lines = [
            f'*{club.name}* — {league.name}',
            TeamCaptionBuilder._head_line(league.flag, country, founded),
        ]
        lines.extend(TeamCaptionBuilder._stadium_lines(sports_team))
        if rank:
            lines.append(f'📊 {rank}º na tabela')
        if global_rank:
            lines.append(f'🏆 #{global_rank}º mais valioso do mundo')
        lines.extend(TeamCaptionBuilder._squad_lines(club))
        return '\n'.join(lines)

    @staticmethod
    def _head_line(flag: str, country: str, founded: str) -> str:
        line = f'\n{flag} {country}' if country else f'\n{flag}'
        if founded:
            line += f'   📅 {founded}'
        return line

    @staticmethod
    def _stadium_lines(sports_team: SportsDBTeam | None) -> list[str]:
        if not sports_team or not sports_team.stadium:
            return []
        lines = [f'🏟️ {sports_team.stadium}']
        if sports_team.capacity:
            cap = TeamCaptionBuilder._format_capacity(sports_team.capacity)
            lines.append(f'💺 {cap} lugares')
        return lines

    @staticmethod
    def _squad_lines(club: TmSquadStats) -> list[str]:
        lines: list[str] = []
        if club.squad_size:
            squad_line = f'👥 {club.squad_size} jogadores'
            if club.avg_age:
                squad_line += f'   ⌀ {club.avg_age} anos'
            lines.append(squad_line)
        if club.foreigners_count:
            foreign_line = f'🌍 {club.foreigners_count} estrangeiros'
            if club.foreigners_pct:
                foreign_line += f' ({club.foreigners_pct}%)'
            lines.append(foreign_line)
        if club.market_value:
            lines.append(f'💰 {club.market_value}')
        return lines

    @staticmethod
    def _format_capacity(raw: str) -> str:
        try:
            return f'{int(raw):,}'.replace(',', '.')
        except ValueError:
            return raw
