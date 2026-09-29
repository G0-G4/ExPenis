import asyncio

import httpx
import pytest

from src.expenis.core import cache
from src.expenis.core.service import exchage_rate_service as fx


class _Response:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _Client:
    def __init__(self, handler):
        self._handler = handler

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None, timeout=None):
        return await self._handler(url, params, timeout)


def _install(monkeypatch, handler) -> None:
    monkeypatch.setattr(fx.httpx, "AsyncClient", lambda *args, **kwargs: _Client(handler))


def _cbr():
    return _Response(200, {"Valute": {"USD": {"Value": 90.0}, "EUR": {"Value": 100.0}}})


def _quote(rate: str):
    return _Response(200, {"Realtime Currency Exchange Rate": {"5. Exchange Rate": rate}})


@pytest.fixture(autouse=True)
def _reset_fx_state(tmp_path, monkeypatch):
    cache._cache.clear()
    fx._av_calls.clear()
    fx._last_rates = None
    monkeypatch.setattr(fx, "CRYPTO_RATES_PATH", tmp_path / "crypto_rates.json")
    yield
    cache._cache.clear()
    fx._av_calls.clear()
    fx._last_rates = None


@pytest.mark.asyncio
async def test_crypto_quotes_use_3s_timeout(monkeypatch):
    seen = []

    async def handler(url, params, timeout):
        seen.append((url, params, timeout))
        if "cbr-xml-daily" in url:
            return _cbr()
        rate = "2" if params["from_currency"] == "BTC" else "3"
        return _quote(rate)

    _install(monkeypatch, handler)
    rates = await fx.get_course()

    assert rates["Valute"]["BTC"]["Value"] == 180.0
    assert rates["Valute"]["ETH"]["Value"] == 270.0
    av = [call for call in seen if "alphavantage" in call[0]]
    assert [call[1]["from_currency"] for call in av] == ["BTC", "ETH"]
    assert [call[2] for call in av] == [3.0, 3.0]
    assert [call[2] for call in seen if "cbr-xml-daily" in call[0]] == [None]


@pytest.mark.asyncio
async def test_alphavantage_timeout_keeps_fiat_rates_and_is_cached(monkeypatch):
    seen = []

    async def handler(url, params, timeout):
        seen.append((url, timeout))
        if "cbr-xml-daily" in url:
            return _cbr()
        raise httpx.ReadTimeout("timed out")

    _install(monkeypatch, handler)
    assert await fx.get_currency_exchange_rate("USD") == 90.0
    assert await fx.get_currency_exchange_rate("EUR") == 100.0
    await fx.get_currency_exchange_rate("USD")

    av = [call for call in seen if "alphavantage" in call[0]]
    binance = [call for call in seen if "binance" in call[0]]
    assert len(av) == 1
    assert av[0][1] == fx.AV_TIMEOUT_SECONDS
    assert len(binance) == 1
    assert binance[0][1] == fx.AV_TIMEOUT_SECONDS
    assert len([call for call in seen if "cbr-xml-daily" in call[0]]) == 1
    assert len(fx._av_calls) == 1


@pytest.mark.asyncio
async def test_rate_limit_payload_does_not_fail_fiat_rates(monkeypatch):
    av = []

    async def handler(url, params, timeout):
        if "cbr-xml-daily" in url:
            return _cbr()
        if "binance" in url:
            return _Response(503, {})
        av.append(params["from_currency"])
        return _Response(200, {"Information": "standard API rate limit is 25 requests per day"})

    _install(monkeypatch, handler)
    assert await fx.get_currency_exchange_rate("USD") == 90.0
    assert av == ["BTC"]


@pytest.mark.asyncio
async def test_daily_limit_skips_call_and_reuses_previous_crypto(monkeypatch):
    av = []

    async def handler(url, params, timeout):
        if "cbr-xml-daily" in url:
            return _cbr()
        if "binance" in url:
            return _Response(503, {})
        av.append(params["from_currency"])
        return _quote("2" if params["from_currency"] == "BTC" else "4")

    _install(monkeypatch, handler)
    first = await fx.get_course()
    assert first["Valute"]["BTC"]["Value"] == 180.0
    assert first["Valute"]["ETH"]["Value"] == 360.0

    cache._cache.clear()
    fx._av_calls.clear()
    fx._av_calls.extend([0.0] * fx.AV_MAX_REQUESTS_PER_DAY)
    monkeypatch.setattr(fx.time, "monotonic", lambda: 10.0)

    second = await fx.get_course()
    assert av == ["BTC", "ETH"]
    assert second["Valute"]["BTC"]["Value"] == 180.0
    assert second["Valute"]["ETH"]["Value"] == 360.0


@pytest.mark.asyncio
async def test_minute_limit_allows_only_remaining_slot(monkeypatch):
    av = []

    async def handler(url, params, timeout):
        if "cbr-xml-daily" in url:
            return _cbr()
        if "binance" in url:
            return _Response(503, {})
        av.append(params["from_currency"])
        return _quote("1")

    _install(monkeypatch, handler)
    now = 5_000.0
    monkeypatch.setattr(fx.time, "monotonic", lambda: now)
    fx._av_calls.extend([now] * (fx.AV_MAX_REQUESTS_PER_MINUTE - 1))

    rates = await fx.get_course()
    assert av == ["BTC"]
    assert rates["Valute"]["BTC"]["Value"] == 90.0
    assert "ETH" not in rates["Valute"]


@pytest.mark.asyncio
async def test_binance_fills_crypto_when_alphavantage_times_out(monkeypatch):
    seen = []

    async def handler(url, params, timeout):
        seen.append(url)
        if "cbr-xml-daily" in url:
            return _cbr()
        if "binance" in url:
            assert timeout == 3.0
            assert params["symbols"] == '["BTCUSDT","ETHUSDT"]'
            return _Response(200, [
                {"symbol": "BTCUSDT", "price": "2"},
                {"symbol": "ETHUSDT", "price": "4"},
            ])
        raise httpx.ReadTimeout("timed out")

    _install(monkeypatch, handler)
    rates = await fx.get_course()

    assert rates["Valute"]["BTC"]["Value"] == 180.0
    assert rates["Valute"]["ETH"]["Value"] == 360.0
    assert any("binance" in url for url in seen)
    saved = fx.CRYPTO_RATES_PATH.read_text()
    assert '"BTC": 180.0' in saved
    assert '"ETH": 360.0' in saved


@pytest.mark.asyncio
async def test_saved_crypto_rate_used_when_quotes_fail(monkeypatch, tmp_path):
    fx.CRYPTO_RATES_PATH.write_text('{"BTC": 123.0, "ETH": 45.0}')

    async def handler(url, params, timeout):
        if "cbr-xml-daily" in url:
            return _cbr()
        if "binance" in url:
            return _Response(503, {})
        raise httpx.ReadTimeout("timed out")

    _install(monkeypatch, handler)
    assert await fx.get_currency_exchange_rate("BTC") == 123.0
    assert await fx.get_currency_exchange_rate("ETH") == 45.0


def test_calls_older_than_a_day_do_not_consume_budget():
    now = 1_000_000.0
    expired = now - fx.AV_DAY_WINDOW_SECONDS - 1
    fx._av_calls.extend([expired] * fx.AV_MAX_REQUESTS_PER_DAY)
    assert fx._av_call_allowed(now) is True


@pytest.mark.asyncio
async def test_parallel_refreshes_share_one_upstream_fetch(monkeypatch):
    cbr_calls = 0
    av_calls = 0

    async def handler(url, params, timeout):
        nonlocal cbr_calls, av_calls
        await asyncio.sleep(0.05)
        if "cbr-xml-daily" in url:
            cbr_calls += 1
            return _cbr()
        av_calls += 1
        return _quote("2")

    _install(monkeypatch, handler)
    await asyncio.gather(fx.get_course(), fx.get_course(), fx.get_course())
    assert cbr_calls == 1
    assert av_calls == 2
