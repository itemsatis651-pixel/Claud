import pandas as pd

from src.data.pipeline import fetch_and_clean

HOUR_MS = 3600 * 1000


def candle(ts_ms):
    return [ts_ms, 100, 110, 90, 105, 10]


class FakeClient:
    def __init__(self, candles):
        self._candles = candles

    def fetch_ohlcv_history(self, symbol, timeframe, since_ms, until_ms=None, limit=300):
        return [c for c in self._candles if c[0] >= since_ms]


def make_config(tmp_path):
    return {
        "data": {
            "exchange": "okx",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "history_start": "1970-01-01T00:00:00Z",
            "cache_dir": str(tmp_path / "raw"),
            "processed_dir": str(tmp_path / "processed"),
            "max_retries": 1,
            "retry_backoff_seconds": 0,
        }
    }


def test_fetch_and_clean_writes_cache_and_processed_files(tmp_path):
    config = make_config(tmp_path)
    client = FakeClient([candle(0), candle(HOUR_MS), candle(2 * HOUR_MS)])

    df, report = fetch_and_clean(config=config, exchange_client=client)

    assert len(df) == 3
    assert report["new_candles_fetched"] == 3
    assert (tmp_path / "raw" / "okx_BTC-USDT_1h.parquet").exists()
    assert (tmp_path / "processed" / "okx_BTC-USDT_1h.csv").exists()


def test_fetch_and_clean_resumes_from_cache_incrementally(tmp_path):
    config = make_config(tmp_path)

    first_client = FakeClient([candle(0), candle(HOUR_MS)])
    df1, report1 = fetch_and_clean(config=config, exchange_client=first_client)
    assert len(df1) == 2

    # İkinci çalıştırmada sahte istemci daha önce çekilmiş mumları da döndürüyor
    # (gerçek borsa davranışına benzer), ama pipeline cache sayesinde sadece
    # since_ms'den itibaren isteyecek ve önceki kayıtlarla tekrar birleştirecek.
    second_client = FakeClient([candle(0), candle(HOUR_MS), candle(2 * HOUR_MS)])
    df2, report2 = fetch_and_clean(config=config, exchange_client=second_client)

    assert len(df2) == 3
    assert report2["new_candles_fetched"] == 1
    assert report2["duplicates_removed"] == 0
