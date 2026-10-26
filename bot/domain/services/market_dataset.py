"""Players and club squads from the transfermarkt-datasets dump, cached in memory.

Transfermarkt itself blocks datacenter IPs, so market values come from this weekly
public scrape instead of live pages.
"""

import csv
import gzip
import io
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from typing import ClassVar

import anyio
import structlog

from bot.data.football import BR_TIMEZONE
from bot.data.market_dataset import (
    CLUB_BADGE_URL,
    MARKET_DATASET_STALE_AFTER,
    MARKET_DATASET_TTL,
    MARKET_DATASET_URL,
)
from bot.data.nationality_flags import nationality_flag
from bot.domain.models.football import TmPlayer, TmSquadStats
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


@dataclass(frozen=True)
class _Snapshot:
    loaded_at: datetime
    players: dict[str, list[TmPlayer]] = field(default_factory=dict)
    clubs: dict[str, list[TmSquadStats]] = field(default_factory=dict)


class MarketDataset:
    _TTL: ClassVar = MARKET_DATASET_TTL
    _ALL: ClassVar[str] = ''
    _MILLION: ClassVar[int] = 1_000_000
    _THOUSAND: ClassVar[int] = 1_000
    _snapshot: ClassVar[_Snapshot | None] = None

    @classmethod
    async def players(cls, league_id: str = _ALL) -> list[TmPlayer]:
        snapshot = await cls._current()
        return snapshot.players.get(league_id, [])

    @classmethod
    async def clubs(cls, league_id: str = _ALL) -> list[TmSquadStats]:
        snapshot = await cls._current()
        return snapshot.clubs.get(league_id, [])

    @classmethod
    async def _current(cls) -> _Snapshot:
        snapshot = cls._snapshot
        if snapshot is None or datetime.now(UTC) - snapshot.loaded_at >= cls._TTL:
            snapshot = await cls._load()
            cls._snapshot = snapshot
        return snapshot

    @classmethod
    async def _load(cls) -> _Snapshot:
        players = await cls._download('players')
        clubs = await cls._download('clubs')
        return await anyio.to_thread.run_sync(cls._parse, players, clubs)

    @staticmethod
    async def _download(table: str) -> bytes:
        response = await HttpClient.get(MARKET_DATASET_URL.format(table=table))
        response.raise_for_status()
        last_modified = response.headers.get('last-modified')
        if last_modified:
            age = datetime.now(UTC) - parsedate_to_datetime(last_modified)
            if age > MARKET_DATASET_STALE_AFTER:
                logger.warning('market_dataset_stale', last_modified=last_modified)
        return response.content

    @classmethod
    def _parse(cls, players_csv: bytes, clubs_csv: bytes) -> _Snapshot:
        clubs = list(_rows(clubs_csv))
        season = max(row['last_season'] for row in clubs)
        current = sorted(
            (
                row
                for row in _rows(players_csv)
                if row['last_season'] == season and row['market_value_in_eur']
            ),
            key=lambda row: -int(row['market_value_in_eur']),
        )
        snapshot = _Snapshot(loaded_at=datetime.now(UTC))
        squad_values: dict[str, int] = defaultdict(int)
        for row in current:
            player = cls._player(row)
            snapshot.players.setdefault(cls._ALL, []).append(player)
            league_id = row['current_club_domestic_competition_id']
            snapshot.players.setdefault(league_id, []).append(player)
            squad_values[row['current_club_id']] += int(row['market_value_in_eur'])

        current_clubs = [row for row in clubs if row['last_season'] == season]
        for row in sorted(current_clubs, key=lambda row: -squad_values[row['club_id']]):
            club = cls._club(row, squad_values[row['club_id']])
            snapshot.clubs.setdefault(cls._ALL, []).append(club)
            snapshot.clubs.setdefault(row['domestic_competition_id'], []).append(club)
        return snapshot

    @classmethod
    def _player(cls, row: dict[str, str]) -> TmPlayer:
        return TmPlayer(
            name=row['name'],
            position=row['sub_position'],
            age=_age(row['date_of_birth']),
            nationality=row['country_of_citizenship'],
            club=row['current_club_name'],
            club_id=row['current_club_id'],
            market_value=cls._euros(int(row['market_value_in_eur'])),
            photo_url=row['image_url'],
            badge_url=CLUB_BADGE_URL.format(club_id=row['current_club_id']),
            nationality_flag_emoji=nationality_flag(row['country_of_citizenship']),
        )

    @classmethod
    def _club(cls, row: dict[str, str], squad_value: int) -> TmSquadStats:
        return TmSquadStats(
            market_value=cls._euros(squad_value),
            squad_size=row['squad_size'],
            avg_age=row['average_age'].replace('.', ','),
            foreigners_count=row['foreigners_number'],
            foreigners_pct=row['foreigners_percentage'].replace('.', ','),
            club_id=row['club_id'],
            name=row['name'],
            badge_url=CLUB_BADGE_URL.format(club_id=row['club_id']),
        )

    @classmethod
    def _euros(cls, value: int) -> str:
        if value < cls._MILLION:
            return f'€ {value // cls._THOUSAND} mil.'
        millions = f'{value / cls._MILLION:,.2f}'
        return f'€ {millions.replace(",", "X").replace(".", ",").replace("X", ".")} mi.'


def _rows(gzipped_csv: bytes) -> Iterator[dict[str, str]]:
    # Streamed: decoding the whole players dump at once peaks around 100 MB.
    with gzip.open(io.BytesIO(gzipped_csv), 'rt', encoding='utf-8') as text:
        yield from csv.DictReader(text)


def _age(date_of_birth: str) -> int:
    if not date_of_birth:
        return 0
    born = date.fromisoformat(date_of_birth[:10])
    today = datetime.now(BR_TIMEZONE).date()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
