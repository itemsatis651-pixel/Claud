import numpy as np
import pandas as pd
import pytest

from src.indicators.momentum import macd, rsi, stochastic
from src.indicators.pipeline import apply_indicators
from src.indicators.registry import available_indicators, get_indicator
from src.indicators.trend import ema, sma
from src.indicators.volatility import bollinger


def make_df(closes):
    n = len(closes)
    closes = pd.Series(closes, dtype="float64")
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": pd.Series([10.0] * n),
        }
    )


def test_registry_has_all_expected_indicators():
    assert set(["sma", "ema", "rsi", "macd", "bollinger", "stochastic"]).issubset(available_indicators())
    assert get_indicator("sma") is sma


def test_sma_basic_rolling_mean():
    df = make_df([1, 2, 3, 4, 5, 6])
    out = sma(df, windows=(3,))
    values = out["sma_3"]

    assert pd.isna(values.iloc[0])
    assert pd.isna(values.iloc[1])
    assert values.iloc[2] == pytest.approx(2.0)  # (1+2+3)/3
    assert values.iloc[5] == pytest.approx(5.0)  # (4+5+6)/3


def test_ema_with_span_one_equals_raw_series():
    df = make_df([10, 20, 15, 30, 25])
    out = ema(df, windows=(1,))
    assert out["ema_1"].tolist() == pytest.approx(df["close"].tolist())


def test_rsi_is_100_for_strictly_increasing_series():
    closes = list(range(1, 40))  # sürekli artan, hiç düşüş yok
    df = make_df(closes)
    out = rsi(df, period=14)
    values = out["rsi_14"]
    assert values.iloc[-1] == pytest.approx(100.0)


def test_rsi_is_0_for_strictly_decreasing_series():
    closes = list(range(100, 60, -1))  # sürekli düşen, hiç kazanç yok
    df = make_df(closes)
    out = rsi(df, period=14)
    values = out["rsi_14"]
    assert values.iloc[-1] == pytest.approx(0.0)


def test_macd_is_zero_for_flat_price_series():
    df = make_df([100.0] * 60)
    out = macd(df, fast=12, slow=26, signal=9)
    assert out["macd_12_26_9_line"].iloc[-1] == pytest.approx(0.0)
    assert out["macd_12_26_9_signal"].iloc[-1] == pytest.approx(0.0)
    assert out["macd_12_26_9_hist"].iloc[-1] == pytest.approx(0.0)


def test_bollinger_bands_collapse_to_price_for_flat_series():
    df = make_df([50.0] * 25)
    out = bollinger(df, window=20, num_std=2)
    assert out["bb_20_2_mid"].iloc[-1] == pytest.approx(50.0)
    assert out["bb_20_2_upper"].iloc[-1] == pytest.approx(50.0)
    assert out["bb_20_2_lower"].iloc[-1] == pytest.approx(50.0)


def test_stochastic_is_100_when_close_repeatedly_at_period_high():
    n = 20
    highs = np.arange(1, n + 1, dtype="float64")
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
            "open": highs,
            "high": highs,
            "low": highs - 1,
            "close": highs,  # kapanış her mumda periyodun zirvesinde
            "volume": np.full(n, 10.0),
        }
    )
    out = stochastic(df, period=5, smooth_k=1, d_period=1)
    k = out["stoch_5_1_1_k"]
    assert k.iloc[-1] == pytest.approx(100.0)


def test_stochastic_is_0_when_close_repeatedly_at_period_low():
    n = 20
    lows = np.arange(n, 0, -1, dtype="float64")
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
            "open": lows,
            "high": lows + 1,
            "low": lows,
            "close": lows,  # kapanış her mumda periyodun dibinde
            "volume": np.full(n, 10.0),
        }
    )
    out = stochastic(df, period=5, smooth_k=1, d_period=1)
    k = out["stoch_5_1_1_k"]
    assert k.iloc[-1] == pytest.approx(0.0)


def test_apply_indicators_respects_enabled_flag():
    df = make_df(np.linspace(100, 200, 60))
    config = {
        "sma": {"enabled": True, "windows": [10]},
        "ema": {"enabled": False, "windows": [10]},
    }
    result = apply_indicators(df, config)

    assert "sma_10" in result.columns
    assert "ema_10" not in result.columns


def test_apply_indicators_adds_all_configured_columns():
    df = make_df(np.linspace(100, 200, 60))
    config = {
        "sma": {"windows": [20]},
        "ema": {"windows": [12]},
        "rsi": {"period": 14},
        "macd": {"fast": 12, "slow": 26, "signal": 9},
        "bollinger": {"window": 20, "num_std": 2},
    }
    result = apply_indicators(df, config)

    expected_new_columns = {
        "sma_20",
        "ema_12",
        "rsi_14",
        "macd_12_26_9_line",
        "macd_12_26_9_signal",
        "macd_12_26_9_hist",
        "bb_20_2_mid",
        "bb_20_2_upper",
        "bb_20_2_lower",
    }
    assert expected_new_columns.issubset(result.columns)
    # orijinal OHLCV sütunları korunmalı
    assert {"timestamp", "open", "high", "low", "close", "volume"}.issubset(result.columns)


def test_apply_indicators_with_unknown_indicator_raises():
    df = make_df([1, 2, 3])
    with pytest.raises(KeyError):
        apply_indicators(df, {"does_not_exist": {}})
