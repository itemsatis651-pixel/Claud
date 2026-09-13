"""Ham OHLCV verisini temizleyen ve kalite raporu üreten fonksiyonlar.

Bu modül tamamen saf (network'e dokunmaz) tutuldu ki hem test edilmesi kolay
olsun hem de başka bir veri kaynağından gelen OHLCV listeleri de aynı
fonksiyonlarla temizlenebilsin.
"""

import pandas as pd

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

_TIMEFRAME_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}


def timeframe_to_seconds(timeframe):
    """'1h', '15m', '4h', '1d' gibi ccxt zaman dilimi string'ini saniyeye çevirir."""
    unit = timeframe[-1]
    if unit not in _TIMEFRAME_UNIT_SECONDS:
        raise ValueError(f"Desteklenmeyen zaman dilimi birimi: {timeframe}")
    value = int(timeframe[:-1])
    return value * _TIMEFRAME_UNIT_SECONDS[unit]


def ohlcv_list_to_df(raw_candles):
    """ccxt'nin döndürdüğü [[ts, o, h, l, c, v], ...] listesini DataFrame'e çevirir."""
    df = pd.DataFrame(raw_candles, columns=OHLCV_COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def detect_gaps(df, timeframe):
    """Beklenen mum aralığına göre eksik mumları (zaman boşluklarını) bulur.

    Döner: [{"after": ..., "before": ..., "missing_candles": int}, ...]
    """
    if len(df) < 2:
        return []

    expected_delta = pd.Timedelta(seconds=timeframe_to_seconds(timeframe))
    timestamps = df["timestamp"].reset_index(drop=True)
    deltas = timestamps.diff()

    gaps = []
    for i in range(1, len(timestamps)):
        delta = deltas.iloc[i]
        if delta > expected_delta:
            missing_candles = int(delta / expected_delta) - 1
            gaps.append(
                {
                    "after": timestamps.iloc[i - 1].isoformat(),
                    "before": timestamps.iloc[i].isoformat(),
                    "missing_candles": missing_candles,
                }
            )
    return gaps


def clean_ohlcv(df, timeframe):
    """OHLCV verisini temizler ve neler yapıldığını anlatan bir rapor döner.

    Adımlar: kopya zaman damgalarını at, zamana göre sırala, eksik (NaN)
    satırları at, mantıksız OHLC ilişkilerini (örn. high < low) at, kalan
    veride zaman boşluklarını tespit et (silmeden, sadece raporla).
    """
    report = {"input_rows": len(df)}

    df = df.drop_duplicates(subset="timestamp", keep="last")
    report["duplicates_removed"] = report["input_rows"] - len(df)

    df = df.sort_values("timestamp").reset_index(drop=True)

    before_na = len(df)
    df = df.dropna(subset=OHLCV_COLUMNS)
    report["nan_rows_dropped"] = before_na - len(df)

    invalid_mask = (
        (df["high"] < df["low"])
        | (df["high"] < df["open"])
        | (df["high"] < df["close"])
        | (df["low"] > df["open"])
        | (df["low"] > df["close"])
        | (df["volume"] < 0)
    )
    report["invalid_ohlc_rows_dropped"] = int(invalid_mask.sum())
    df = df.loc[~invalid_mask].reset_index(drop=True)

    gaps = detect_gaps(df, timeframe)
    report["gap_count"] = len(gaps)
    report["gaps"] = gaps

    report["output_rows"] = len(df)
    if len(df) > 0:
        report["start"] = df["timestamp"].iloc[0].isoformat()
        report["end"] = df["timestamp"].iloc[-1].isoformat()

    return df, report
