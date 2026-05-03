"""Classification zones per league — Libertadores, Europa League, relegation, etc."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationZone:
    name: str
    start: int
    end: int
    emoji: str


CHAMPIONS_LEAGUE = 'Champions League'
EUROPA_LEAGUE = 'Europa League'
CONFERENCE_LEAGUE = 'Conference League'

LEAGUE_ZONES: dict[str, list[ClassificationZone]] = {
    'pl': [
        ClassificationZone(CHAMPIONS_LEAGUE, 1, 4, '🟢'),
        ClassificationZone(EUROPA_LEAGUE, 5, 5, '🟡'),
        ClassificationZone(CONFERENCE_LEAGUE, 6, 6, '🟠'),
        ClassificationZone('Rebaixamento', 18, 20, '🔴'),
    ],
    'la': [
        ClassificationZone(CHAMPIONS_LEAGUE, 1, 4, '🟢'),
        ClassificationZone(EUROPA_LEAGUE, 5, 6, '🟡'),
        ClassificationZone(CONFERENCE_LEAGUE, 7, 7, '🟠'),
        ClassificationZone('Rebaixamento', 18, 20, '🔴'),
    ],
    'bl': [
        ClassificationZone(CHAMPIONS_LEAGUE, 1, 4, '🟢'),
        ClassificationZone(EUROPA_LEAGUE, 5, 6, '🟡'),
        ClassificationZone(CONFERENCE_LEAGUE, 7, 7, '🟠'),
        ClassificationZone('Rebaixamento', 16, 18, '🔴'),
    ],
    'sa': [
        ClassificationZone(CHAMPIONS_LEAGUE, 1, 4, '🟢'),
        ClassificationZone(EUROPA_LEAGUE, 5, 6, '🟡'),
        ClassificationZone(CONFERENCE_LEAGUE, 7, 7, '🟠'),
        ClassificationZone('Rebaixamento', 18, 20, '🔴'),
    ],
    'l1': [
        ClassificationZone(CHAMPIONS_LEAGUE, 1, 3, '🟢'),
        ClassificationZone('Champions League Playoff', 4, 4, '🟡'),
        ClassificationZone(EUROPA_LEAGUE, 5, 5, '🟡'),
        ClassificationZone(CONFERENCE_LEAGUE, 6, 6, '🟠'),
        ClassificationZone('Rebaixamento', 15, 18, '🔴'),
    ],
    'br': [
        ClassificationZone('Libertadores', 1, 6, '🟢'),
        ClassificationZone('Sul-Americana', 7, 12, '🟡'),
        ClassificationZone('Rebaixamento', 17, 20, '🔴'),
    ],
    'ar': [
        ClassificationZone('Libertadores', 1, 6, '🟢'),
        ClassificationZone('Sul-Americana', 7, 12, '🟡'),
        ClassificationZone('Rebaixamento', 25, 28, '🔴'),
    ],
    'uy': [
        ClassificationZone('Libertadores', 1, 4, '🟢'),
        ClassificationZone('Sul-Americana', 5, 8, '🟡'),
        ClassificationZone('Rebaixamento', 13, 16, '🔴'),
    ],
    'ec': [
        ClassificationZone('Libertadores', 1, 4, '🟢'),
        ClassificationZone('Sul-Americana', 5, 8, '🟡'),
        ClassificationZone('Rebaixamento', 14, 16, '🔴'),
    ],
    'co': [
        ClassificationZone('Libertadores', 1, 4, '🟢'),
        ClassificationZone('Sul-Americana', 5, 8, '🟡'),
        ClassificationZone('Rebaixamento', 19, 20, '🔴'),
    ],
}

MEDAL_EMOJIS: dict[int, str] = {
    1: '🥇',
    2: '🥈',
    3: '🥉',
}

DEFAULT_ZONE_EMOJI = '⚪'
