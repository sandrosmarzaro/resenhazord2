import httpx
import structlog

from bot.data.currency import COINGECKO_IDS, ROBUX, ROBUX_STORE_PACK
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class AssetPrices:
    RATES_URL = 'https://cdn.moneyconvert.net/api/latest.json'
    COINGECKO_URL = 'https://api.coingecko.com/api/v3/simple/price'

    @classmethod
    async def in_reais(cls) -> dict[str, float]:
        # CoinGecko goes first so the ,moeda contract call still reaches it on the
        # GitHub runners that moneyconvert blocks.
        coingecko_prices = await cls._coingecko_prices()
        response = await HttpClient.get(cls.RATES_URL)
        response.raise_for_status()
        rates = response.json()['rates']
        reais_per_dollar = rates['BRL']
        prices = {code: reais_per_dollar / rate for code, rate in rates.items()}
        prices[ROBUX] = reais_per_dollar * ROBUX_STORE_PACK.dollars / ROBUX_STORE_PACK.robux
        return prices | coingecko_prices

    @classmethod
    async def _coingecko_prices(cls) -> dict[str, float]:
        params = {'ids': ','.join(COINGECKO_IDS.values()), 'vs_currencies': 'brl'}
        try:
            response = await HttpClient.get(cls.COINGECKO_URL, params=params)
            response.raise_for_status()
            coins = response.json()
            return {code: coins[coin_id]['brl'] for code, coin_id in COINGECKO_IDS.items()}
        except (httpx.HTTPError, KeyError) as error:
            logger.warning('upstream_failed', upstream='coingecko', error=str(error))
            return {}
