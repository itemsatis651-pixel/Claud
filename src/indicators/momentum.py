"""Momentum indikatörleri: RSI ve MACD."""

from src.indicators.registry import register_indicator


@register_indicator("rsi")
def rsi(df, period=14, price_col="close"):
    """Wilder'ın orijinal yöntemiyle RSI (Relative Strength Index).

    Kazanç/kayıpların ortalaması, `period` uzunluğunda basit ortalama yerine
    Wilder'ın önerdiği üstel düzeltme (alpha = 1/period) ile hesaplanır —
    bu, TradingView/çoğu platformun varsayılan RSI hesaplama yöntemidir.
    """
    delta = df[price_col].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))
    # avg_loss == 0 iken rs = inf/NaN olur; bu dönemde hiç düşüş olmadığı için RSI=100.
    rsi_values = rsi_values.where(avg_loss != 0, 100)

    return {f"rsi_{period}": rsi_values}


@register_indicator("macd")
def macd(df, fast=12, slow=26, signal=9, price_col="close"):
    """MACD: hızlı/yavaş EMA farkı ve bunun sinyal hattı + histogramı."""
    ema_fast = df[price_col].ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = df[price_col].ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line

    prefix = f"macd_{fast}_{slow}_{signal}"
    return {
        f"{prefix}_line": macd_line,
        f"{prefix}_signal": signal_line,
        f"{prefix}_hist": histogram,
    }


@register_indicator("stochastic")
def stochastic(df, period=14, smooth_k=3, d_period=3, high_col="high", low_col="low", close_col="close"):
    """Stokastik Osilatör (Slow Stochastic: ham %K önce `smooth_k` ile
    yumuşatılır, %D bunun `d_period` hareketli ortalamasıdır).
    """
    lowest_low = df[low_col].rolling(window=period, min_periods=period).min()
    highest_high = df[high_col].rolling(window=period, min_periods=period).max()

    raw_k = 100 * (df[close_col] - lowest_low) / (highest_high - lowest_low)
    k = raw_k.rolling(window=smooth_k, min_periods=smooth_k).mean()
    d = k.rolling(window=d_period, min_periods=d_period).mean()

    prefix = f"stoch_{period}_{smooth_k}_{d_period}"
    return {f"{prefix}_k": k, f"{prefix}_d": d}
