import numpy as np
import pandas as pd

from src.backtest.regime import classify_regime


def make_df(closes):
    n = len(closes)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
            "close": closes,
        }
    )


def test_warmup_period_is_unclassified():
    # sma_period=5, slope_lookback=3 -> ilk (5-1)+3=7 bar None olmalı
    closes = list(range(1, 21))
    df = make_df(closes)

    regime = classify_regime(df, sma_period=5, slope_lookback=3, bull_threshold=0.05, bear_threshold=-0.05)

    assert regime.iloc[:7].isna().all()
    assert regime.iloc[7:].notna().all()


def test_strong_uptrend_is_classified_as_bull():
    closes = [100 + 50 * i for i in range(20)]  # dik yükseliş
    df = make_df(closes)

    regime = classify_regime(df, sma_period=5, slope_lookback=3, bull_threshold=0.05, bear_threshold=-0.05)

    assert regime.iloc[-1] == "BOĞA"


def test_strong_downtrend_is_classified_as_bear():
    closes = [1000 - 40 * i for i in range(20)]  # dik düşüş
    df = make_df(closes)

    regime = classify_regime(df, sma_period=5, slope_lookback=3, bull_threshold=0.05, bear_threshold=-0.05)

    assert regime.iloc[-1] == "AYI"


def test_flat_series_is_classified_as_sideways():
    closes = [100.0] * 20
    df = make_df(closes)

    regime = classify_regime(df, sma_period=5, slope_lookback=3, bull_threshold=0.05, bear_threshold=-0.05)

    assert regime.iloc[-1] == "YATAY"


def test_thresholds_control_sensitivity():
    # index7'de slope tam %3: eşik %5 iken YATAY, eşik %1 iken BOĞA olmalı
    closes = [100, 100, 100, 100, 100, 103, 103, 103, 103, 103]
    df = make_df(closes)

    strict = classify_regime(df, sma_period=3, slope_lookback=3, bull_threshold=0.05, bear_threshold=-0.05)
    loose = classify_regime(df, sma_period=3, slope_lookback=3, bull_threshold=0.01, bear_threshold=-0.01)

    assert strict.iloc[7] == "YATAY"
    assert loose.iloc[7] == "BOĞA"
