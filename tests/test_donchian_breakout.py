import numpy as np
import pandas as pd
import pytest

from src.strategies.donchian_breakout import donchian_breakout_strategy
from src.strategies.registry import available_strategies, get_strategy


def make_df(closes, upper, lower, sma):
    n = len(closes)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
            "close": closes,
            "donchian_5_upper": upper,
            "donchian_2_lower": lower,
            "sma_10": sma,
        }
    )


def test_registry_contains_donchian_breakout():
    assert "donchian_breakout" in available_strategies()
    assert get_strategy("donchian_breakout") is donchian_breakout_strategy


def test_buy_when_price_breaks_above_prev_upper_band_and_above_trend_filter():
    # bar1: close(110) > prev_upper(bar0 upper=100) ve close(110) > sma(90) -> AL
    df = make_df(closes=[95.0, 110.0], upper=[100.0, 105.0], lower=[50.0, 60.0], sma=[90.0, 90.0])

    result = donchian_breakout_strategy(df, entry_period=5, exit_period=2, trend_filter_period=10)

    assert result["signal"].iloc[1] == "AL"
    assert result["signal_score"].iloc[1] == 2


def test_no_buy_when_breakout_but_below_trend_filter():
    # bar1: close(110) > prev_upper(100) ama close(110) < sma(150) -> trend filtresi engelliyor -> BEKLE
    df = make_df(closes=[95.0, 110.0], upper=[100.0, 105.0], lower=[50.0, 60.0], sma=[150.0, 150.0])

    result = donchian_breakout_strategy(df, entry_period=5, exit_period=2, trend_filter_period=10)

    assert result["signal"].iloc[1] == "BEKLE"


def test_sell_when_price_breaks_below_prev_lower_band():
    # bar1: close(40) < prev_lower(bar0 lower=50) -> SAT (trend filtresinden bağımsız)
    df = make_df(closes=[95.0, 40.0], upper=[100.0, 105.0], lower=[50.0, 30.0], sma=[200.0, 200.0])

    result = donchian_breakout_strategy(df, entry_period=5, exit_period=2, trend_filter_period=10)

    assert result["signal"].iloc[1] == "SAT"
    assert result["signal_score"].iloc[1] == -2  # trend_score(-1, fiyat sma altında) + breakout_score(-1)


def test_breakout_uses_previous_bar_channel_not_current_bar_lookahead():
    # bar1'in KENDİ upper'ı (105) fiyatın (103) üzerinde olsa bile, kıyaslama
    # bar0'ın upper'ıyla (100) yapılmalı -> 103 > 100 -> breakout TRUE olmalı
    df = make_df(closes=[95.0, 103.0], upper=[100.0, 200.0], lower=[50.0, 60.0], sma=[50.0, 50.0])

    result = donchian_breakout_strategy(df, entry_period=5, exit_period=2, trend_filter_period=10)

    assert result["signal"].iloc[1] == "AL"


def test_hold_when_no_breakout():
    df = make_df(closes=[95.0, 96.0], upper=[100.0, 101.0], lower=[50.0, 51.0], sma=[90.0, 90.0])

    result = donchian_breakout_strategy(df, entry_period=5, exit_period=2, trend_filter_period=10)

    assert result["signal"].iloc[1] == "BEKLE"


def test_missing_indicator_column_raises_keyerror():
    df = pd.DataFrame({"close": [1, 2, 3]})
    with pytest.raises(KeyError):
        donchian_breakout_strategy(df)
