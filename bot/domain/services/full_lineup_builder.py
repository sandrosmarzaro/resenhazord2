"""Build full team lineup with field image."""

import asyncio

from bot.data.football import LEAGUES
from bot.data.football_formations import Formation
from bot.domain.services.football_field.build_field import build_football_field
from bot.domain.services.lineup_builder import LineupBuilder
from bot.domain.services.player_assets import PlayerAssets
from bot.domain.services.transfermarkt.service import TransfermarktService


class FullLineupBuilder:
    @staticmethod
    async def build(
        league_code: str | None,
        formation: Formation,
        top_n: int,
    ) -> tuple[bytes, str]:
        league = LEAGUES.get(league_code) if league_code else None

        if league:
            all_players = await TransfermarktService.fetch_league_full_squad(league)
            ordered = LineupBuilder.from_league_squad(all_players, formation)
        else:
            max_pages = TransfermarktService.POSITION_MAX_PAGES
            if top_n > 0:
                max_pages = max(
                    1,
                    min(
                        (top_n + TransfermarktService.PLAYERS_PER_PAGE - 1)
                        // TransfermarktService.PLAYERS_PER_PAGE,
                        TransfermarktService.GLOBAL_MAX_PAGES,
                    ),
                )
            ordered = await LineupBuilder.from_position_queries(formation, max_pages, top_n)

        photos_ordered, badge_images = await PlayerAssets.fetch(ordered)

        names = [p.name if p else '' for p in ordered]
        flag_emojis = [
            (p.nationality_flag_emoji if p and p.nationality_flag_emoji else None) for p in ordered
        ]
        overlays = list(zip(flag_emojis, badge_images, strict=False))
        total_value = TransfermarktService.sum_market_values(ordered)
        field_image = await asyncio.to_thread(
            build_football_field, photos_ordered, names, formation, overlays, total_value
        )

        caption = f'⚽ *Escalação Aleatória* — {formation.name}'
        if total_value:
            caption += f'\n💰 {total_value}'
        return field_image, caption
