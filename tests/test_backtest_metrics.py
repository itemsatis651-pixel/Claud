import numpy as np
import pandas as pd
import pytest

from src.backtest.metrics import compute_metrics, segment_return_pct


def make_equity(values, freq="1h"):
    n = len(values)
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC"))


def test_total_return_and_final_equity():
    equity = make_equity([1000.0, 1100.0, 1250.0])
    trades = pd.DataFrame(columns=["pnl", "return_pct", "bars_held"])

    m = compute_metrics(equity, trades, periods_per_year=8766, initial_capital=1000.0)

    assert m["final_equity"] == pytest.approx(1250.0)
    assert m["total_return_pct"] == pytest.approx(25.0)


def test_max_drawdown():
    equity = make_equity([100.0, 120.0, 80.0, 90.0, 150.0, 60.0])
    trades = pd.DataFrame(columns=["pnl", "return_pct", "bars_held"])

    m = compute_metrics(equity, trades, periods_per_year=8766, initial_capital=100.0)

    # running max: [100,120,120,120,150,150] -> min(equity/running_max-1) = 60/150-1 = -0.6
    assert m["max_drawdown_pct"] == pytest.approx(-60.0)


def test_trade_stats_win_rate_profit_factor_avg_win_loss():
    equity = make_equity([1000.0, 1050.0, 1000.0])
    trades = pd.DataFrame(
        [
            {"pnl": 100.0, "return_pct": 0.10, "bars_held": 5},
            {"pnl": -50.0, "return_pct": -0.05, "bars_held": 3},
            {"pnl": 200.0, "return_pct": 0.20, "bars_held": 10},
        ]
    )

    m = compute_metrics(equity, trades, periods_per_year=8766, initial_capital=1000.0)

    assert m["num_trades"] == 3
    assert m["win_rate_pct"] == pytest.approx(2 / 3 * 100)
    assert m["avg_win_pct"] == pytest.approx(15.0)  # mean(10%, 20%)
    assert m["avg_loss_pct"] == pytest.approx(-5.0)
    assert m["profit_factor"] == pytest.approx(300.0 / 50.0)
    assert m["avg_bars_held"] == pytest.approx(6.0)


def test_no_trades_yields_nan_trade_stats():
    equity = make_equity([1000.0, 1000.0])
    trades = pd.DataFrame(columns=["pnl", "return_pct", "bars_held"])

    m = compute_metrics(equity, trades, periods_per_year=8766, initial_capital=1000.0)

    assert m["num_trades"] == 0
    assert np.isnan(m["win_rate_pct"])
    assert np.isnan(m["profit_factor"])


def test_cagr_matches_manual_calculation_for_one_year_span():
    periods_per_year = 100
    n = periods_per_year + 1  # tam 1 yıl kapsasın (years = n/periods_per_year)
    equity = make_equity(list(np.linspace(1000.0, 2000.0, n)), freq="D")

    m = compute_metrics(equity, pd.DataFrame(columns=["pnl", "return_pct", "bars_held"]), periods_per_year, 1000.0)

    years = n / periods_per_year
    expected_cagr = ((2000.0 / 1000.0) ** (1 / years) - 1) * 100
    assert m["cagr_pct"] == pytest.approx(expected_cagr)


def test_segment_return_pct_basic():
    equity = make_equity([100.0, 110.0, 121.0, 130.0])
    start = equity.index[1]
    end = equity.index[3]

    ret = segment_return_pct(equity, start=start, end=end)

    # [start, end) -> equity[1] ve equity[2] -> 121/110-1
    assert ret == pytest.approx((121.0 / 110.0 - 1) * 100)


def test_segment_return_pct_returns_nan_for_empty_range():
    equity = make_equity([100.0, 110.0])
    start = equity.index[-1] + pd.Timedelta(days=10)

    ret = segment_return_pct(equity, start=start)

    assert np.isnan(ret)
