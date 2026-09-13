import pandas as pd
import pytest

from src.backtest.engine import run_backtest


def make_df(signals, opens, closes):
    n = len(signals)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
            "open": opens,
            "close": closes,
            "signal": signals,
        }
    )


def test_entry_and_exit_execute_on_next_bar_open_not_same_bar_close():
    # AL sinyali bar1'de üretildi (bar1'in KAPANIŞINA bakılarak), ama işlem
    # bar2'nin AÇILIŞINDA gerçekleşmeli - aynı barın kapanışından DEĞİL.
    signals = ["BEKLE", "AL", "BEKLE", "SAT", "BEKLE"]
    opens = [100.0, 101.0, 102.0, 103.0, 104.0]
    closes = [100.5, 101.5, 102.5, 103.5, 104.5]
    df = make_df(signals, opens, closes)

    result = run_backtest(df, initial_capital=1000.0, fee_bps=0.0, slippage_bps=0.0)
    trades = result["trades"]

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["entry_price"] == pytest.approx(102.0)  # bar2 open, bar1'in close'u (101.5) DEĞİL
    assert trade["exit_price"] == pytest.approx(104.0)  # bar4 open, bar3'ün close'u (103.5) DEĞİL
    assert trade["bars_held"] == 2

    expected_units = 1000.0 / 102.0
    expected_capital_at_exit = expected_units * 104.0
    assert trade["capital_at_exit"] == pytest.approx(expected_capital_at_exit)
    assert trade["pnl"] == pytest.approx(expected_capital_at_exit - 1000.0)


def test_fee_and_slippage_reduce_returns_as_expected():
    signals = ["BEKLE", "AL", "BEKLE", "SAT", "BEKLE"]
    opens = [100.0, 101.0, 102.0, 103.0, 104.0]
    closes = [100.5, 101.5, 102.5, 103.5, 104.5]
    df = make_df(signals, opens, closes)

    result = run_backtest(df, initial_capital=1000.0, fee_bps=100.0, slippage_bps=100.0)  # %1 + %1
    trade = result["trades"].iloc[0]

    entry_fill = 102.0 * 1.01
    entry_fee = 1000.0 * 0.01
    expected_units = (1000.0 - entry_fee) / entry_fill
    exit_fill = 104.0 * 0.99
    proceeds = expected_units * exit_fill
    exit_fee = proceeds * 0.01
    expected_cash = proceeds - exit_fee

    assert trade["entry_price"] == pytest.approx(entry_fill)
    assert trade["exit_price"] == pytest.approx(exit_fill)
    assert trade["capital_at_exit"] == pytest.approx(expected_cash)


def test_repeated_al_signal_while_in_position_is_a_noop():
    signals = ["BEKLE", "AL", "AL", "SAT", "BEKLE"]
    opens = [100.0, 101.0, 102.0, 103.0, 104.0]
    closes = [100.5, 101.5, 102.5, 103.5, 104.5]
    df = make_df(signals, opens, closes)

    result = run_backtest(df, initial_capital=1000.0, fee_bps=0.0, slippage_bps=0.0)

    assert len(result["trades"]) == 1  # ikinci AL yoksayıldı, tek işlem açıldı
    assert result["trades"].iloc[0]["entry_price"] == pytest.approx(102.0)


def test_sat_signal_while_flat_is_a_noop():
    signals = ["BEKLE", "SAT", "BEKLE"]
    opens = [100.0, 101.0, 102.0]
    closes = [100.5, 101.5, 102.5]
    df = make_df(signals, opens, closes)

    result = run_backtest(df, initial_capital=1000.0, fee_bps=0.0, slippage_bps=0.0)

    assert len(result["trades"]) == 0
    assert result["position"].tolist() == [0, 0, 0]
    assert result["equity"].tolist() == pytest.approx([1000.0, 1000.0, 1000.0])


def test_open_position_at_end_is_not_counted_as_closed_trade_but_equity_reflects_it():
    signals = ["BEKLE", "AL", "BEKLE"]
    opens = [100.0, 101.0, 102.0]
    closes = [100.5, 101.5, 102.5]
    df = make_df(signals, opens, closes)

    result = run_backtest(df, initial_capital=1000.0, fee_bps=0.0, slippage_bps=0.0)

    assert result["open_position_at_end"] is True
    assert len(result["trades"]) == 0  # hiç kapanmadı, "işlem" olarak sayılmıyor
    # AL sinyali bar1'de üretildi, işlem bar2'nin açılışında (102.0) gerçekleşti
    expected_units = 1000.0 / 102.0
    assert result["equity"].iloc[-1] == pytest.approx(expected_units * 102.5)  # mark-to-market


def test_equity_index_preserves_timezone():
    signals = ["BEKLE", "AL", "BEKLE"]
    opens = [100.0, 101.0, 102.0]
    closes = [100.5, 101.5, 102.5]
    df = make_df(signals, opens, closes)

    result = run_backtest(df, initial_capital=1000.0)

    assert result["equity"].index.tz is not None
