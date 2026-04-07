# ruff: noqa: T201, C901, PLR0912, PLR2004, RUF100, E501, S311
"""
Debug script for the ,time command — runs the full data pipeline locally
without needing Docker. Tests squad value parsing, standings, and name matching.

Usage:
    uv run python scripts/test_time.py [league_code]

    league_code: pl, la, bl, sa, l1, br, ar, uy, ec, co  (default: l1)
"""

import asyncio
import random
import sys

sys.path.insert(0, '.')

from bot.data.football import LEAGUE_CODES, LEAGUES
from bot.domain.commands.football_team import FootballTeamCommand
from bot.domain.services.thesportsdb import TheSportsDBService
from bot.domain.services.transfermarkt import TransfermarktService


def _sep(label: str) -> None:
    print(f'\n{"─" * 50}')
    print(f'  {label}')
    print('─' * 50)


async def main(liga_code: str) -> None:
    league = LEAGUES[liga_code]
    print(f'\n🔍 Testing ,time for [{liga_code}] {league.name}')

    _sep('TheSportsDB — teams')
    teams = await TheSportsDBService.get_teams(league)
    if not teams:
        print('  ❌ No teams returned')
    else:
        for t in teams[:5]:
            print(f'  • {t.name!r:30s} stadium={t.stadium!r}  cap={t.capacity!r}')
        if len(teams) > 5:
            print(f'  ... and {len(teams) - 5} more')

    _sep('TheSportsDB — standings')
    standings = await TheSportsDBService.get_standings(league)
    if not standings:
        print('  ❌ No standings returned (season may be wrong or not started)')
    else:
        for s in standings[:5]:
            print(f'  #{s.rank:2d}  {s.team!r}')
        if len(standings) > 5:
            print(f'  ... and {len(standings) - 5} more')

    _sep('Transfermarkt — squad values')
    squad_values = await TransfermarktService.fetch_squad_values(league)
    if not squad_values:
        print('  ❌ squad_values is EMPTY — parsing failed or page blocked')
    else:
        for name, stats in list(squad_values.items())[:5]:
            print(
                f'  {name!r:35s} '
                f'size={stats.squad_size!r:4s} '
                f'age={stats.avg_age!r:5s} '
                f'foreign={stats.foreigners_count!r}/{stats.foreigners_pct!r}% '
                f'value={stats.market_value!r}'
            )
        if len(squad_values) > 5:
            print(f'  ... and {len(squad_values) - 5} more')

    _sep('Name matching (TheSportsDB → Transfermarkt)')
    if not teams:
        print('  (no teams to match)')
    else:
        for team in (teams if len(teams) <= 8 else random.sample(teams, 8)):  # noqa: S311
            rank = FootballTeamCommand._find_rank(team.name, standings)
            stats = FootballTeamCommand._find_squad_stats(team.name, squad_values)
            rank_str = f'#{rank}' if rank else '—'
            val_str = stats.market_value if stats else '—'
            size_str = stats.squad_size if stats else '—'
            match_icon = '✅' if stats else '❌'
            print(f'  {match_icon} {team.name!r:30s} rank={rank_str:3s}  size={size_str:3s}  value={val_str}')

    _sep('Caption preview (random team)')
    if teams:
        team = random.choice(teams)  # noqa: S311
        rank = FootballTeamCommand._find_rank(team.name, standings)
        stats = FootballTeamCommand._find_squad_stats(team.name, squad_values)
        caption = FootballTeamCommand._build_team_caption(
            team, league.name, league.flag, rank, stats
        )
        print(caption)


if __name__ == '__main__':
    code = sys.argv[1] if len(sys.argv) > 1 else 'l1'
    if code not in LEAGUE_CODES:
        print(f'Unknown league code: {code!r}')
        print(f'Available: {LEAGUE_CODES}')
        sys.exit(1)
    asyncio.run(main(code))
