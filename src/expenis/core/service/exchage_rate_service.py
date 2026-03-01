
import httpx

from .. import cache


@cache.cached(ttl_seconds=60*60*4)
async def get_course():
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        if res.status_code != 200:
            raise RuntimeError(f"request ended with code {res.status_code}")
    return res.json()


async def get_currency_exchange_rate(currency_code: str) -> float:
    rates = await get_course()
    valutes = rates.get("Valute", dict())
    valutes["RUB"] = {"Value": 1.0}
    valute = valutes.get(currency_code, dict())
    if "Value" not in valute:
        raise RuntimeError(f"exchange rate not found for {currency_code}")
    return valute.get("Value")
