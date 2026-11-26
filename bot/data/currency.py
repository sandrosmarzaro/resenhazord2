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

FIAT = AssetGroup(CURRENCY_FLAGS)
CRYPTO = AssetGroup(CRYPTO_SYMBOLS)
METALS = AssetGroup(METAL_MEDALS, unit='oz ')
ROBUX_GROUP = AssetGroup(frozendict({ROBUX: '🎮'}), note=' (preço da loja)')

ASSET_GROUPS: tuple[AssetGroup, ...] = (FIAT, CRYPTO, METALS, ROBUX_GROUP)

# Lowercase and accentless, matched against the casefolded, accentless filter.
# Every code (usd, btc, robux) also answers to itself.
GROUP_NAMES: frozendict[str, AssetGroup] = frozendict(
    {
        'moedas': FIAT,
        'fiat': FIAT,
        'cripto': CRYPTO,
        'crypto': CRYPTO,
        'criptomoedas': CRYPTO,
        'metais': METALS,
        'metal': METALS,
    }
)

ASSET_NAMES: frozendict[str, str] = frozendict(
    {
        'dolar': 'USD',
        'dolar americano': 'USD',
        'euro': 'EUR',
        'libra': 'GBP',
        'libra esterlina': 'GBP',
        'franco': 'CHF',
        'franco suico': 'CHF',
        'iene': 'JPY',
        'yen': 'JPY',
        'yuan': 'CNY',
        'renminbi': 'CNY',
        'dolar de hong kong': 'HKD',
        'dolar hong kong': 'HKD',
        'dolar canadense': 'CAD',
        'dolar australiano': 'AUD',
        'rupia': 'INR',
        'rupia indiana': 'INR',
        'kwanza': 'AOA',
        'peso': 'ARS',
        'peso argentino': 'ARS',
        'bitcoin': 'BTC',
        'ethereum': 'ETH',
        'ether': 'ETH',
        'solana': 'SOL',
        'dogecoin': 'DOGE',
        'ouro': 'XAU',
        'prata': 'XAG',
        'platina': 'XPT',
    }
)

# moneyconvert has no Solana rate, so CoinGecko prices it.
COINGECKO_IDS: frozendict[str, str] = frozendict({'SOL': 'solana'})

# Robux has no market rate. Smallest pack in Roblox's browser store, checked 2026-10-18.
ROBUX_STORE_PACK = StorePack(robux=500, dollars=4.99)
