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
