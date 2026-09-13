import pandas as pd
import pytest

from src.data.clean import (
    clean_ohlcv,
    detect_gaps,
    ohlcv_list_to_df,
    timeframe_to_seconds,
)


def make_candle(ts_ms, o, h, l, c, v):
    return [ts_ms, o, h, l, c, v]


HOUR_MS = 3600 * 1000


def test_timeframe_to_seconds():
    assert timeframe_to_seconds("1h") == 3600
    assert timeframe_to_seconds("15m") == 900
    assert timeframe_to_seconds("1d") == 86400
    with pytest.raises(ValueError):
        timeframe_to_seconds("1x")


def test_ohlcv_list_to_df_converts_timestamp_to_utc_datetime():
    raw = [make_candle(0, 100, 110, 90, 105, 10)]
    df = ohlcv_list_to_df(raw)
    assert str(df["timestamp"].dt.tz) == "UTC"
    assert df.loc[0, "open"] == 100


def test_clean_removes_duplicate_timestamps():
    raw = [
        make_candle(0, 100, 110, 90, 100, 10),
        make_candle(0, 999, 999, 999, 999, 999),  # aynı zaman damgası, son kaydı tut
        make_candle(HOUR_MS, 100, 110, 90, 100, 10),
    ]
    df = ohlcv_list_to_df(raw)
    cleaned, report = clean_ohlcv(df, "1h")

    assert report["duplicates_removed"] == 1
    assert len(cleaned) == 2
    assert cleaned.loc[0, "open"] == 999


def test_clean_detects_gap():
    raw = [
        make_candle(0, 100, 110, 90, 100, 10),
        make_candle(3 * HOUR_MS, 100, 110, 90, 100, 10),  # 2 mum eksik (1h ve 2h)
    ]
    df = ohlcv_list_to_df(raw)
    cleaned, report = clean_ohlcv(df, "1h")

    assert report["gap_count"] == 1
    assert report["gaps"][0]["missing_candles"] == 2


def test_clean_drops_invalid_ohlc_rows():
    raw = [
        make_candle(0, 100, 110, 90, 100, 10),           # geçerli
        make_candle(HOUR_MS, 100, 90, 110, 100, 10),      # high < low -> geçersiz
        make_candle(2 * HOUR_MS, 100, 110, 90, 100, -5),  # negatif hacim -> geçersiz
    ]
    df = ohlcv_list_to_df(raw)
    cleaned, report = clean_ohlcv(df, "1h")

    assert report["invalid_ohlc_rows_dropped"] == 2
    assert len(cleaned) == 1


def test_detect_gaps_returns_empty_for_fewer_than_two_rows():
    df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    assert detect_gaps(df, "1h") == []
