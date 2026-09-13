"""Oynaklık indikatörleri: Bollinger Bands."""

from src.indicators.registry import register_indicator


@register_indicator("bollinger")
def bollinger(df, window=20, num_std=2, price_col="close"):
    """Bollinger Bands: hareketli ortalama +/- N standart sapma."""
    middle = df[price_col].rolling(window=window, min_periods=window).mean()
    std = df[price_col].rolling(window=window, min_periods=window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std

    prefix = f"bb_{window}_{num_std}"
    return {
        f"{prefix}_mid": middle,
        f"{prefix}_upper": upper,
        f"{prefix}_lower": lower,
    }
