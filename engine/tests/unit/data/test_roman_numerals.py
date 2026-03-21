import pytest

from bot.data.roman_numerals import to_roman


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        (1, 'I'),
        (4, 'IV'),
        (9, 'IX'),
        (14, 'XIV'),
        (42, 'XLII'),
        (99, 'XCIX'),
        (100, 'C'),
        (399, 'CCCXCIX'),
        (500, 'D'),
        (1000, 'M'),
        (1994, 'MCMXCIV'),
        (3999, 'MMMCMXCIX'),
    ],
)
def test_to_roman(number, expected):
    assert to_roman(number) == expected
