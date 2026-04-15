"""Fetch global top team."""

import random

from bot.data.football import LEAGUES_BY_TM_ID
from bot.domain.models.football import TmClub
from bot.domain.services.transfermarkt.service import TransfermarktService


class GlobalTopTeam:
    @staticmethod
    async def fetch(top_n: int) -> TmClub | None:
        if top_n <= 0:
            return None
        top_clubs = await TransfermarktService.fetch_top_clubs(top_n)
        return random.choice(top_clubs) if top_clubs else None  # noqa: S311

    @staticmethod
    def find_league(club: TmClub) -> str | None:
        league_info = LEAGUES_BY_TM_ID.get(club.league_tm_id)
        return league_info.code if league_info else None
