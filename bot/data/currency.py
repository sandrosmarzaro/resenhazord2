"""Currency data for the currency conversion command."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrencyInfo:
    code: str
    name: str
    symbol: str
    decimals: int


CURRENCIES: dict[str, CurrencyInfo] = {
    'USD': CurrencyInfo('USD', 'Dólar Americano', '$', 2),
    'EUR': CurrencyInfo('EUR', 'Euro', '€', 2),
    'GBP': CurrencyInfo('GBP', 'Libra Esterlina', '£', 2),
    'CHF': CurrencyInfo('CHF', 'Franco Suíço', 'Fr', 2),
    'JPY': CurrencyInfo('JPY', 'Iene Japonês', '¥', 0),
    'CNY': CurrencyInfo('CNY', 'Yuan Chinês', '¥', 2),
    'HKD': CurrencyInfo('HKD', 'Dólar de Hong Kong', '$', 2),
    'CAD': CurrencyInfo('CAD', 'Dólar Canadense', '$', 2),
    'AUD': CurrencyInfo('AUD', 'Dólar Australiano', '$', 2),
    'INR': CurrencyInfo('INR', 'Rúpia Indiana', '₹', 2),
    'AOA': CurrencyInfo('AOA', 'Kwanza Angolano', 'Kz', 2),
    'ARS': CurrencyInfo('ARS', 'Peso Argentino', '$', 2),
}

CURRENCY_EMOJI: dict[str, str] = {
    'USD': '💵',
    'EUR': '€',
    'GBP': '£',
    'CHF': '₣',
    'JPY': '¥',
    'CNY': '¥',
    'HKD': '💰',
    'CAD': '💵',
    'AUD': '💵',
    'INR': '₹',
    'AOA': 'Kz',
    'ARS': '💰',
}
