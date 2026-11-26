"""Assets the currency command prices in reais, grouped as the reply lists them."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetGroup:
    icons: frozendict[str, str]
    unit: str = ''
    note: str = ''


@dataclass(frozen=True)
class StorePack:
    robux: int
    dollars: float


CURRENCY_FLAGS: frozendict[str, str] = frozendict(
    {
        'USD': '🇺🇸',
        'EUR': '🇪🇺',
        'GBP': '🇬🇧',
        'CHF': '🇨🇭',
        'JPY': '🇯🇵',
        'CNY': '🇨🇳',
        'HKD': '🇭🇰',
        'CAD': '🇨🇦',
        'AUD': '🇦🇺',
        'INR': '🇮🇳',
        'AOA': '🇦🇴',
        'ARS': '🇦🇷',
    }
)

CRYPTO_SYMBOLS: frozendict[str, str] = frozendict(
    {
        'BTC': '₿',
        'ETH': 'Ξ',
        'SOL': '◎',
        'DOGE': '🐕',
    }
)

METAL_MEDALS: frozendict[str, str] = frozendict(
    {
        'XAU': '🥇',
        'XAG': '🥈',
        'XPT': '⚪',
    }
)

ROBUX = 'Robux'

ASSET_GROUPS: tuple[AssetGroup, ...] = (
    AssetGroup(CURRENCY_FLAGS),
    AssetGroup(CRYPTO_SYMBOLS),
    AssetGroup(METAL_MEDALS, unit='oz '),
    AssetGroup(frozendict({ROBUX: '🎮'}), note=' (preço da loja)'),
)

# moneyconvert has no Solana rate, so CoinGecko prices it.
COINGECKO_IDS: frozendict[str, str] = frozendict({'SOL': 'solana'})

# Robux has no market rate. Smallest pack in Roblox's browser store, checked 2026-10-18.
ROBUX_STORE_PACK = StorePack(robux=500, dollars=4.99)
