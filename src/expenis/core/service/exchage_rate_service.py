import json
import logging
import time
from collections import deque
from pathlib import Path

import httpx

from .. import cache
from ...observability.runtime import operation
from opentelemetry.trace import SpanKind, Status, StatusCode
from ...config import ALPHAVANTAGE_KEY

logger = logging.getLogger(__name__)

crypto_list = ["BTC", "ETH"]

# Free tier (alphavantage.co/premium): 5 requests/minute, 25 requests/day.
AV_TIMEOUT_SECONDS = 3.0
AV_MAX_REQUESTS_PER_MINUTE = 5
AV_MAX_REQUESTS_PER_DAY = 25
AV_MINUTE_WINDOW_SECONDS = 60.0
AV_DAY_WINDOW_SECONDS = 24 * 60 * 60.0

_BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"
_BINANCE_SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
CRYPTO_RATES_PATH = Path("data/crypto_rates.json")

_av_calls: deque[float] = deque()
_last_rates: dict | None = None


async def _observed_get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    provider = (
        "cbr"
        if url.startswith("https://www.cbr-xml-daily.ru/")
        else "binance"
        if url.startswith("https://api.binance.com/")
        else "alphavantage"
    )
    response: httpx.Response | None = None
    with operation(
        f"http.{provider}",
        SpanKind.CLIENT,
        failed=lambda: response is not None and not response.is_success,
    ) as span:
        response = await client.get(url, **kwargs)
        if span is not None:
            span.set_attributes({"provider": provider, "status": response.status_code})
            if not response.is_success:
                span.set_status(Status(StatusCode.ERROR))
        return response


def _prune_av_calls(now: float) -> None:
    cutoff = now - AV_DAY_WINDOW_SECONDS
    while _av_calls and _av_calls[0] <= cutoff:
        _av_calls.popleft()


def _av_call_allowed(now: float) -> bool:
    _prune_av_calls(now)
    if len(_av_calls) >= AV_MAX_REQUESTS_PER_DAY:
        return False
    minute_ago = now - AV_MINUTE_WINDOW_SECONDS
    in_minute = sum(1 for ts in _av_calls if ts > minute_ago)
    return in_minute < AV_MAX_REQUESTS_PER_MINUTE


def _record_av_call(now: float) -> None:
    _av_calls.append(now)


def _crypto_rub_rate(payload: dict, usd_rub: float) -> float | None:
    quote = payload.get("Realtime Currency Exchange Rate")
    if not isinstance(quote, dict) or "5. Exchange Rate" not in quote:
        return None
    try:
        return float(quote["5. Exchange Rate"]) * usd_rub
    except (TypeError, ValueError):
        return None


def _saved_crypto_rates() -> dict:
    try:
        payload = json.loads(CRYPTO_RATES_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        code: {"Value": value} for code, value in payload.items() if isinstance(value, (int, float))
    }


def _apply_previous_crypto(rates: dict) -> None:
    previous = (_last_rates or {}).get("Valute") or _saved_crypto_rates()
    valute = rates.setdefault("Valute", {})
    for crypto in crypto_list:
        if crypto not in valute and crypto in previous:
            valute[crypto] = previous[crypto]


def _persist_crypto(rates: dict) -> None:
    valute = rates.get("Valute") or {}
    payload = {}
    for code in crypto_list:
        value = (valute.get(code) or {}).get("Value")
        if isinstance(value, (int, float)):
            payload[code] = value
    if not payload:
        return
    try:
        CRYPTO_RATES_PATH.parent.mkdir(parents=True, exist_ok=True)
        CRYPTO_RATES_PATH.write_text(json.dumps(payload))
    except OSError:
        logger.warning("rates_persist_failed")


async def _fill_crypto_from_binance(
    client: httpx.AsyncClient,
    rates: dict,
    usd_rub: float,
    missing: list[str],
) -> list[str]:
    symbols = [_BINANCE_SYMBOLS[code] for code in missing if code in _BINANCE_SYMBOLS]
    if not symbols:
        return []
    logger.warning("rates_fallback")
    try:
        res = await _observed_get(
            client,
            _BINANCE_URL,
            params={"symbols": json.dumps(symbols, separators=(",", ":"))},
            timeout=AV_TIMEOUT_SECONDS,
        )
    except httpx.TransportError:
        logger.warning("provider_transport_error")
        return []
    if res.status_code != 200:
        logger.warning("provider_http_error")
        return []
    payload = res.json()
    if not isinstance(payload, list):
        logger.warning("provider_payload_error")
        return []
    by_symbol = {
        item.get("symbol"): item.get("price") for item in payload if isinstance(item, dict)
    }
    fetched: list[str] = []
    for code in missing:
        raw = by_symbol.get(_BINANCE_SYMBOLS.get(code, ""))
        if raw is None:
            continue
        try:
            rub = float(raw) * usd_rub
        except (TypeError, ValueError):
            continue
        rates.setdefault("Valute", {})[code] = {"Value": rub}
        fetched.append(code)
    return fetched


@cache.cached(ttl_seconds=60 * 60 * 4)
async def get_course():
    global _last_rates
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    crypto_url = "https://www.alphavantage.co/query"
    async with httpx.AsyncClient() as client:
        res = await _observed_get(client, url)
        if res.status_code != 200:
            logger.error("provider_http_error")
            raise RuntimeError(f"request ended with code {res.status_code}")
        rates = res.json()
        usd_rub = (rates.get("Valute") or {}).get("USD", {}).get("Value")
        fetched: list[str] = []
        for crypto in crypto_list:
            now = time.monotonic()
            if usd_rub is None:
                logger.error("provider_payload_error")
                break
            if not _av_call_allowed(now):
                logger.warning("provider_rate_limited")
                break
            _record_av_call(now)
            try:
                res = await _observed_get(
                    client,
                    crypto_url,
                    params={
                        "apikey": ALPHAVANTAGE_KEY,
                        "function": "CURRENCY_EXCHANGE_RATE",
                        "from_currency": crypto,
                        "to_currency": "USD",
                    },
                    timeout=AV_TIMEOUT_SECONDS,
                )
            except httpx.TransportError:
                # Timeouts and dropped connections alike: crypto is optional.
                logger.warning("provider_transport_error")
                break
            if res.status_code != 200:
                logger.error("provider_http_error")
                break
            payload = res.json()
            if not isinstance(payload, dict):
                logger.warning("provider_payload_error")
                break
            rub_rate = _crypto_rub_rate(payload, float(usd_rub))
            if rub_rate is None:
                logger.warning("provider_quote_missing")
                break
            rates.setdefault("Valute", {})[crypto] = {"Value": rub_rate}
            fetched.append(crypto)
        missing = [code for code in crypto_list if code not in (rates.get("Valute") or {})]
        if missing and usd_rub is not None:
            fetched.extend(await _fill_crypto_from_binance(client, rates, float(usd_rub), missing))
        _apply_previous_crypto(rates)
        _last_rates = rates
        _persist_crypto(rates)
        available = [code for code in crypto_list if code in (rates.get("Valute") or {})]
        logger.info("rates_fetched")
        return rates


async def get_currency_exchange_rate(currency_code: str) -> float:
    rates = await get_course()
    valutes = rates.get("Valute", dict())
    valutes["RUB"] = {"Value": 1.0}
    valute = valutes.get(currency_code, dict())
    if "Value" not in valute:
        raise RuntimeError(f"exchange rate not found for {currency_code}")
    return valute.get("Value")


async def convert_to_rubles(amount: float, currency_code: str) -> float | None:
    if amount is None:
        return amount
    rate = await get_currency_exchange_rate(currency_code)
    return amount * rate
