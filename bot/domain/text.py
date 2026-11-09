import unicodedata


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize('NFD', text)
    return ''.join(char for char in decomposed if unicodedata.category(char) != 'Mn')
