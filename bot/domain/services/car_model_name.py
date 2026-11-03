import re

from bot.data.car import SPEC_TOKEN, SPEC_WORD_BASE, SPEC_WORD_WIKI
from bot.data.car_brands import FIPE_BRANDS


class CarModelName:
    _BRAND_NAMES_LOWER: frozenset[str] = frozenset(b.name.lower() for b in FIPE_BRANDS)
    _BRAND_SUFFIX_PATTERN = re.compile(
        r'^(.+?)\s+(?:motors?|automobiles?|automotive|group|corporation|trucks?)$'
    )

    @staticmethod
    def base(model_name: str) -> str:
        words = model_name.strip().split()
        stop = next(
            (i for i, w in enumerate(words) if SPEC_TOKEN.match(w) or w.lower() in SPEC_WORD_BASE),
            -1,
        )
        return ' '.join(words[:stop] if stop > 0 else words)

    @staticmethod
    def wiki(model_name: str) -> str:
        words = []
        for token in model_name.strip().split():
            words.extend(token.split('/'))
        stop = next(
            (
                i
                for i, w in enumerate(words)
                if SPEC_TOKEN.match(w) or w.rstrip('.,').lower() in SPEC_WORD_WIKI
            ),
            -1,
        )
        return ' '.join(words[:stop] if stop > 0 else words)

    @classmethod
    def is_brand_only_page(cls, page_title: str) -> bool:
        if not page_title:
            return False
        title_lower = page_title.lower()
        if title_lower in cls._BRAND_NAMES_LOWER:
            return True
        match = cls._BRAND_SUFFIX_PATTERN.match(title_lower)
        return bool(match and match.group(1) in cls._BRAND_NAMES_LOWER)
