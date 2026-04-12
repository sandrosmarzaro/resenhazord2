"""Transfermarkt public API — facade over client and parser."""

import re
from typing import ClassVar

from bot.domain.models.football import TmPlayer
from bot.domain.services.transfermarkt.client import TransfermarktClient

_VALUE_RE = re.compile(r'€\s*([\d.,]+)\s*(mi\.|mil\.)')


class TransfermarktService(TransfermarktClient):
    POSITION_ROLES: ClassVar[dict[str, str]] = {
        'Goleiro': 'GK',
        'Goalkeeper': 'GK',
        'Zagueiro': 'CB',
        'Zagueiro Central': 'CB',
        'Defensor Central': 'CB',
        'Centre-Back': 'CB',
        'Lateral Esq.': 'LB',
        'Lateral Esquerdo': 'LB',
        'Lateral-Esquerdo': 'LB',
        'Left-Back': 'LB',
        'Lateral Dir.': 'RB',
        'Lateral Direito': 'RB',
        'Lateral-Direito': 'RB',
        'Right-Back': 'RB',
        'Volante': 'DM',
        'Segundo Volante': 'DM',
        'Meia Defensivo': 'DM',
        'Defensive Midfield': 'DM',
        'Meia-Central': 'CM',
        'Meia Central': 'CM',
        'Central Midfield': 'CM',
        'Meia-Esquerda': 'CM',
        'Meia-Direita': 'CM',
        'Right Midfield': 'CM',
        'Left Midfield': 'CM',
        'Meia Ofensivo': 'AM',
        'Meia Atacante': 'AM',
        'Attacking Midfield': 'AM',
        'Centroavante': 'ST',
        'Seg. Atacante': 'ST',
        'Segundo Atacante': 'ST',
        'Atacante de apoio': 'ST',
        'Centre-Forward': 'ST',
        'Second Striker': 'ST',
        'Ponta Esquerda': 'LW',
        'Left Winger': 'LW',
        'Ponta Direita': 'RW',
        'Right Winger': 'RW',
    }

    @staticmethod
    def parse_market_value_millions(value_str: str) -> float:
        m = _VALUE_RE.search(value_str)
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
