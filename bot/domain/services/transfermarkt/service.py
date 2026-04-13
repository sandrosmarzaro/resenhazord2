"""Transfermarkt public API — facade over client and parser."""

import re

from bot.data.transfermarkt_positions import POSITION_ROLES
from bot.domain.models.football import TmPlayer
from bot.domain.services.transfermarkt.client import TransfermarktClient


class TransfermarktService(TransfermarktClient):
    POSITION_ROLES = POSITION_ROLES

    _VALUE_RE = re.compile(r'€\s*([\d.,]+)\s*(mi\.|mil\.)')

    @classmethod
    def parse_market_value_millions(cls, value_str: str) -> float:
        m = cls._VALUE_RE.search(value_str)
        if not m:
            return 0.0
        number_str = m.group(1).replace('.', '').replace(',', '.')
        try:
            number = float(number_str)
        except ValueError:
            return 0.0
        return number / 1000 if m.group(2) == 'mil.' else number

    @staticmethod
    def sum_market_values(players: list[TmPlayer | None]) -> str | None:
        total = sum(
            TransfermarktService.parse_market_value_millions(p.market_value)
            for p in players
            if p and p.market_value
        )
        if total <= 0:
            return None
        us = f'{total:,.2f}'
        br = us.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f'€ {br} mi.'
