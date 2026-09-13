"""Equity curve ve işlem listesinden performans metrikleri hesaplayan modül.

Sharpe/Sortino hesaplarında risksiz faiz oranı **0 varsayıldı** (basitleştirme
- gerçekte kısa vadeli hazine bonosu getirisi çıkarılmalı). Bu, Sharpe'ı
gerçekte olması gerekenden biraz yüksek gösterebilir.
"""

import numpy as np
import pandas as pd


def compute_metrics(equity, trades, periods_per_year, initial_capital):
    """`equity`: timestamp indeksli pd.Series. `trades`: engine.run_backtest'in
    döndürdüğü trades DataFrame'i (boş olabilir)."""
    metrics = {}

    final_equity = float(equity.iloc[-1])
    metrics["initial_capital"] = float(initial_capital)
    metrics["final_equity"] = final_equity
    metrics["total_return_pct"] = (final_equity / initial_capital - 1) * 100

    num_periods = len(equity)
    years = num_periods / periods_per_year if periods_per_year else np.nan
    if years > 0 and final_equity > 0:
        metrics["cagr_pct"] = ((final_equity / initial_capital) ** (1 / years) - 1) * 100
    else:
        metrics["cagr_pct"] = np.nan
    metrics["years_covered"] = years

    bar_returns = equity.pct_change().dropna()
    if len(bar_returns) > 1 and bar_returns.std() > 0:
        metrics["sharpe"] = (bar_returns.mean() / bar_returns.std()) * np.sqrt(periods_per_year)
    else:
        metrics["sharpe"] = np.nan

    downside = bar_returns[bar_returns < 0]
    if len(downside) > 1 and downside.std() > 0:
        metrics["sortino"] = (bar_returns.mean() / downside.std()) * np.sqrt(periods_per_year)
    else:
        metrics["sortino"] = np.nan

    running_max = equity.cummax()
    drawdown = equity / running_max - 1
    metrics["max_drawdown_pct"] = float(drawdown.min()) * 100

    metrics["num_trades"] = len(trades)
    if len(trades) > 0:
        wins = trades[trades["pnl"] > 0]
        losses = trades[trades["pnl"] <= 0]
        metrics["win_rate_pct"] = len(wins) / len(trades) * 100
        metrics["avg_win_pct"] = wins["return_pct"].mean() * 100 if len(wins) > 0 else np.nan
        metrics["avg_loss_pct"] = losses["return_pct"].mean() * 100 if len(losses) > 0 else np.nan
        total_wins = wins["pnl"].sum()
        total_losses = -losses["pnl"].sum()
        metrics["profit_factor"] = (total_wins / total_losses) if total_losses > 0 else np.nan
        metrics["avg_bars_held"] = trades["bars_held"].mean()
    else:
        metrics["win_rate_pct"] = np.nan
        metrics["avg_win_pct"] = np.nan
        metrics["avg_loss_pct"] = np.nan
        metrics["profit_factor"] = np.nan
        metrics["avg_bars_held"] = np.nan

    return metrics


def segment_return_pct(equity, start=None, end=None):
    """`equity` üzerinde [start, end) aralığındaki basit getiriyi (%) döner.
    Aralık boşsa veya tek noktadan azsa NaN döner."""
    segment = equity
    if start is not None:
        segment = segment[segment.index >= start]
    if end is not None:
        segment = segment[segment.index < end]
    if len(segment) < 2:
        return np.nan
    return (segment.iloc[-1] / segment.iloc[0] - 1) * 100
