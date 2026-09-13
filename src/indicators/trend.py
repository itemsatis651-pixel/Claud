"""Trend indikatörleri: basit ve üstel hareketli ortalamalar."""

from src.indicators.registry import register_indicator


@register_indicator("sma")
def sma(df, windows=(20, 50, 200), price_col="close"):
    """Basit hareketli ortalama (Simple Moving Average)."""
    out = {}
    for w in windows:
        out[f"sma_{w}"] = df[price_col].rolling(window=w, min_periods=w).mean()
    return out


@register_indicator("ema")
def ema(df, windows=(12, 26), price_col="close"):
    """Üstel hareketli ortalama (Exponential Moving Average)."""
    out = {}
    for w in windows:
        out[f"ema_{w}"] = df[price_col].ewm(span=w, adjust=False, min_periods=w).mean()
    return out


@register_indicator("donchian")
def donchian(df, periods=(20,), high_col="high", low_col="low"):
    """Donchian Channel: son `period` bardaki en yüksek high / en düşük low.

    Breakout (trend takip) stratejilerinin temel yapı taşı - fiyat üst bandı
    kırınca "yeni N-bar zirvesi", alt bandı kırınca "yeni N-bar dibi" demektir.
    """
    out = {}
    for p in periods:
        upper = df[high_col].rolling(window=p, min_periods=p).max()
        lower = df[low_col].rolling(window=p, min_periods=p).min()
        out[f"donchian_{p}_upper"] = upper
        out[f"donchian_{p}_lower"] = lower
        out[f"donchian_{p}_mid"] = (upper + lower) / 2
    return out
