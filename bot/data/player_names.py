"""Words that belong to a player's surname when abbreviating names on the field."""

SURNAME_PARTICLES: frozenset[str] = frozenset({
    'da', 'das', 'de', 'del', 'der', 'di', 'do', 'dos', 'la', 'le', 'ten', 'ter', 'van', 'von',
})  # fmt: skip

GENERATIONAL_SUFFIXES: frozenset[str] = frozenset({
    'filho', 'jr', 'jr.', 'junior', 'júnior', 'neto', 'sobrinho',
})  # fmt: skip
