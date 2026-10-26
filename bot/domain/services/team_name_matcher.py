"""Pairs club names across sources: official (Transfermarkt) vs short (ESPN, TheSportsDB)."""

import difflib
import re
from typing import ClassVar

from bot.data.football_team_prefixes import CLUB_PREFIXES


class TeamNameMatcher:
    MIN_SCORE: ClassVar[float] = 0.25
    _PREFIX_MIN_LEN: ClassVar[int] = 4
    _WORD_RE: ClassVar[re.Pattern[str]] = re.compile(r'[^\W\d_]{2,}')

    @classmethod
    def best(cls, name: str, candidates: list[str]) -> str | None:
        return cls.pair([name], candidates).get(name)

    @classmethod
    def pair(cls, names: list[str], candidates: list[str]) -> dict[str, str]:
        scored = sorted(
            (
                (cls._score(name, candidate), name, candidate)
                for name in names
                for candidate in candidates
            ),
            reverse=True,
        )
        pairs: dict[str, str] = {}
        taken: set[str] = set()
        for (overlap, _), name, candidate in scored:
            if overlap < cls.MIN_SCORE or name in pairs or candidate in taken:
                continue
            pairs[name] = candidate
            taken.add(candidate)
        return pairs

    @classmethod
    def _score(cls, name: str, candidate: str) -> tuple[float, float]:
        left, right = cls._tokens(name), cls._tokens(candidate)
        overlap = len(left & right) / len(left | right) if left and right else 0.0
        if overlap < cls.MIN_SCORE and cls._related(left, right):
            overlap = cls.MIN_SCORE
        ratio = difflib.SequenceMatcher(None, name.lower(), candidate.lower()).ratio()
        return overlap, ratio

    @classmethod
    def _tokens(cls, name: str) -> set[str]:
        words = set(cls._WORD_RE.findall(name.lower()))
        return words - CLUB_PREFIXES or words

    @classmethod
    def _related(cls, left: set[str], right: set[str]) -> bool:
        if left and right and (left <= right or right <= left):
            return True
        return any(
            a.startswith(b) or b.startswith(a)
            for a in left
            if len(a) >= cls._PREFIX_MIN_LEN
            for b in right
            if len(b) >= cls._PREFIX_MIN_LEN
        )
