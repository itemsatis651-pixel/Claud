import pandas as pd
import pytest

from src.strategies.macd_stochastic import macd_stochastic_strategy
from src.strategies.pipeline import apply_strategy
from src.strategies.registry import available_strategies, get_strategy


def make_indicator_df(hist_values, k_values, d_values):
    n = len(hist_values)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
            "close": [100.0] * n,
            "macd_12_26_9_hist": hist_values,
            "stoch_14_3_3_k": k_values,
            "stoch_14_3_3_d": d_values,
        }
    )


def test_registry_contains_macd_stochastic():
    assert "macd_stochastic" in available_strategies()
    assert get_strategy("macd_stochastic") is macd_stochastic_strategy


def test_buy_signal_on_bullish_confluence():
    # bar1: stokastik %K, %D'yi aşırı satım (<20) bölgesinden yukarı kesiyor + MACD histogram pozitif
    df = make_indicator_df(hist_values=[1.0, 1.0], k_values=[10.0, 25.0], d_values=[15.0, 18.0])

    result = macd_stochastic_strategy(df)

    assert result["signal"].iloc[1] == "AL"
    assert result["signal_score"].iloc[1] == 2
    assert "MACD" in result["signal_reasons"].iloc[1]
    assert "Stokastik" in result["signal_reasons"].iloc[1]


def test_sell_signal_on_bearish_confluence():
    # bar1: stokastik %K, %D'yi aşırı alım (>80) bölgesinden aşağı kesiyor + MACD histogram negatif
    df = make_indicator_df(hist_values=[-1.0, -1.0], k_values=[90.0, 75.0], d_values=[85.0, 82.0])

    result = macd_stochastic_strategy(df)

    assert result["signal"].iloc[1] == "SAT"
    assert result["signal_score"].iloc[1] == -2


def test_hold_when_macd_and_stochastic_disagree():
    # MACD bearish ama stokastik bullish tetik veriyor -> confluence yok
    df = make_indicator_df(hist_values=[-1.0, -1.0], k_values=[10.0, 25.0], d_values=[15.0, 18.0])

    result = macd_stochastic_strategy(df)

    assert result["signal"].iloc[1] == "BEKLE"
    assert result["signal_score"].iloc[1] == 0


def test_hold_when_stochastic_cross_not_from_extreme_zone():
    # kesişim var ama d_prev aşırı satım/alım bölgesinde değil (50 civarı) -> tetik yok
    df = make_indicator_df(hist_values=[1.0, 1.0], k_values=[45.0, 55.0], d_values=[50.0, 52.0])

    result = macd_stochastic_strategy(df)

    assert result["signal"].iloc[1] == "BEKLE"


def test_missing_indicator_column_raises_keyerror():
    df = pd.DataFrame({"close": [1, 2, 3]})
    with pytest.raises(KeyError):
        macd_stochastic_strategy(df)


def test_apply_strategy_requires_active_key():
    df = make_indicator_df([1.0], [50.0], [50.0])
    with pytest.raises(ValueError):
        apply_strategy(df, {})


def test_apply_strategy_dispatches_to_configured_strategy():
    df = make_indicator_df(hist_values=[1.0, 1.0], k_values=[10.0, 25.0], d_values=[15.0, 18.0])
    config = {"active": "macd_stochastic", "macd_stochastic": {"oversold": 20, "overbought": 80}}

    result = apply_strategy(df, config)

    assert result["signal"].iloc[1] == "AL"
