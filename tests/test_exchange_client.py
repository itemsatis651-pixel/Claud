import ccxt
import pytest

from src.data.exchange_client import ExchangeDataClient

HOUR_MS = 3600 * 1000


class FakeExchange:
    """Gerçek ağ çağrısı yapmayan, sayfalanmış sahte OHLCV verisi döndüren borsa."""

    def __init__(self, pages, fail_first_n_calls=0):
        # pages: her biri bir "sayfa" olan mum listelerinin listesi
        self._pages = list(pages)
        self._calls = 0
        self._fail_first_n_calls = fail_first_n_calls

    def parse_timeframe(self, timeframe):
        assert timeframe == "1h"
        return 3600

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        self._calls += 1
        if self._calls <= self._fail_first_n_calls:
            raise ccxt.NetworkError("geçici ağ hatası (test)")
        if not self._pages:
            return []
        return self._pages.pop(0)


def candle(ts_ms):
    return [ts_ms, 100, 110, 90, 105, 10]


def test_fetch_ohlcv_history_paginates_until_limit_not_reached():
    page1 = [candle(0), candle(HOUR_MS)]
    page2 = [candle(2 * HOUR_MS)]
    fake = FakeExchange(pages=[page1, page2])
    client = ExchangeDataClient(exchange=fake, max_retries=1)

    result = client.fetch_ohlcv_history("BTC/USDT", "1h", since_ms=0, limit=2)

    assert [c[0] for c in result] == [0, HOUR_MS, 2 * HOUR_MS]


def test_fetch_ohlcv_history_stops_at_until_ms():
    page1 = [candle(0), candle(HOUR_MS), candle(2 * HOUR_MS)]
    fake = FakeExchange(pages=[page1])
    client = ExchangeDataClient(exchange=fake, max_retries=1)

    result = client.fetch_ohlcv_history("BTC/USDT", "1h", since_ms=0, until_ms=2 * HOUR_MS, limit=10)

    assert [c[0] for c in result] == [0, HOUR_MS]


def test_fetch_ohlcv_history_retries_on_network_error_then_succeeds():
    fake = FakeExchange(pages=[[candle(0)]], fail_first_n_calls=2)
    client = ExchangeDataClient(exchange=fake, max_retries=3, retry_backoff_seconds=0)

    result = client.fetch_ohlcv_history("BTC/USDT", "1h", since_ms=0, until_ms=HOUR_MS, limit=10)

    assert [c[0] for c in result] == [0]
    assert fake._calls == 3


def test_fetch_ohlcv_history_raises_after_exhausting_retries():
    fake = FakeExchange(pages=[[candle(0)]], fail_first_n_calls=5)
    client = ExchangeDataClient(exchange=fake, max_retries=2, retry_backoff_seconds=0)

    with pytest.raises(ccxt.NetworkError):
        client.fetch_ohlcv_history("BTC/USDT", "1h", since_ms=0, until_ms=HOUR_MS, limit=10)


def test_fetch_ohlcv_history_returns_empty_when_no_data():
    fake = FakeExchange(pages=[])
    client = ExchangeDataClient(exchange=fake, max_retries=1)

    result = client.fetch_ohlcv_history("BTC/USDT", "1h", since_ms=0, until_ms=HOUR_MS, limit=10)

    assert result == []
