import asyncio

import httpx

from .. import cache
from ...config import ALPHAVANTAGE_KEY

crypto_list = ['BTC', 'ETH']


@cache.cached(ttl_seconds=60*60*4)
async def get_course():
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    crypto_url = f"https://www.alphavantage.co/query"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        if res.status_code != 200:
            raise RuntimeError(f"request ended with code {res.status_code}")
        rates = res.json()
        for crypto in crypto_list:
            res = await client.get(crypto_url, params={'apikey': ALPHAVANTAGE_KEY, 'function': 'CURRENCY_EXCHANGE_RATE',
                                          'from_currency': crypto, 'to_currency': 'USD'})
            if res.status_code != 200:
                raise RuntimeError(f"request ended with code {rates.status_code}")
            rate = float(res.json().get("Realtime Currency Exchange Rate").get("5. Exchange Rate")) * rates.get('Valute').get('USD').get('Value')
            rates['Valute'][crypto] = {'Value': rate}
            await asyncio.sleep(1)
        return rates


async def get_currency_exchange_rate(currency_code: str) -> float:
    rates = await get_course()
    valutes = rates.get("Valute", dict())
    valutes["RUB"] = {"Value": 1.0}
    valute = valutes.get(currency_code, dict())
    if "Value" not in valute:
        raise RuntimeError(f"exchange rate not found for {currency_code}")
    return valute.get("Value")
