"""Zodiac sign data for the horoscope command."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SignInfo:
    api_name: str
    pt_name: str
    emoji: str
    dates: str


SIGNS: dict[str, SignInfo] = {
    'aries': SignInfo(api_name='aries', pt_name='Áries', emoji='♈', dates='21/03 - 19/04'),
    'taurus': SignInfo(api_name='taurus', pt_name='Touro', emoji='♉', dates='20/04 - 20/05'),
    'gemini': SignInfo(api_name='gemini', pt_name='Gêmeos', emoji='♊', dates='21/05 - 20/06'),
    'cancer': SignInfo(api_name='cancer', pt_name='Câncer', emoji='♋', dates='21/06 - 22/07'),
    'leo': SignInfo(api_name='leo', pt_name='Leão', emoji='♌', dates='23/07 - 22/08'),
    'virgo': SignInfo(api_name='virgo', pt_name='Virgem', emoji='♍', dates='23/08 - 22/09'),
    'libra': SignInfo(api_name='libra', pt_name='Libra', emoji='♎', dates='23/09 - 22/10'),
    'scorpio': SignInfo(api_name='scorpio', pt_name='Escorpião', emoji='♏', dates='23/10 - 21/11'),
    'sagittarius': SignInfo(
        api_name='sagittarius', pt_name='Sagitário', emoji='♐', dates='22/11 - 21/12'
    ),
    'capricorn': SignInfo(
        api_name='capricorn', pt_name='Capricórnio', emoji='♑', dates='22/12 - 19/01'
    ),
    'aquarius': SignInfo(api_name='aquarius', pt_name='Aquário', emoji='♒', dates='20/01 - 18/02'),
    'pisces': SignInfo(api_name='pisces', pt_name='Peixes', emoji='♓', dates='19/02 - 20/03'),
}

# Maps all accepted input names (PT and EN) to API name.
# Portuguese names first (bot is PT-first), then English.
SIGN_LOOKUP: dict[str, str] = {
    # Portuguese
    'áries': 'aries',
    'touro': 'taurus',
    'gêmeos': 'gemini',
    'câncer': 'cancer',
    'leão': 'leo',
    'virgem': 'virgo',
    'libra': 'libra',
    'escorpião': 'scorpio',
    'sagitário': 'sagittarius',
    'capricórnio': 'capricorn',
    'aquário': 'aquarius',
    'peixes': 'pisces',
    # English
    'aries': 'aries',
    'taurus': 'taurus',
    'gemini': 'gemini',
    'cancer': 'cancer',
    'leo': 'leo',
    'virgo': 'virgo',
    'scorpio': 'scorpio',
    'sagittarius': 'sagittarius',
    'capricorn': 'capricorn',
    'aquarius': 'aquarius',
    'pisces': 'pisces',
}

# Formatted list of all signs for usage messages.
SIGN_LIST_TEXT: str = '  '.join(f'{s.emoji} {s.pt_name}' for s in SIGNS.values())
