"""İndikatör katmanını çalıştıran orkestrasyon modülü.

Config'teki `indicators` bölümünü okur, aktif olan indikatörleri OHLCV
DataFrame'ine uygular. Hangi indikatörlerin kayıtlı olduğunu bilmesi için alt
modülleri (trend/momentum/volatility) import eder — her modül kendi
indikatörünü `register_indicator` ile kaydeder (plug-in mekanizması).

Tek başına çalıştırma: `python -m src.indicators.pipeline`
(önce `python -m src.data.pipeline` ile veri üretilmiş olmalı; yoksa
sentetik veriyle demo çalıştırılır.)
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

import src.indicators.momentum  # noqa: F401 - import side effect: indikatörü kaydeder
import src.indicators.trend  # noqa: F401
import src.indicators.volatility  # noqa: F401
from src.indicators.registry import get_indicator
from src.utils.config import load_config

logger = logging.getLogger(__name__)


def apply_indicators(df, indicators_config):
    """Config'te aktif olan indikatörleri df'e uygular, yeni sütunlar ekler.

    `indicators_config` örneği:
        {"sma": {"enabled": True, "windows": [20, 50]}, "rsi": {"period": 14}}
    """
    df = df.copy()
    for name, params in (indicators_config or {}).items():
        params = dict(params or {})
        if not params.pop("enabled", True):
            logger.info("İndikatör devre dışı, atlanıyor: %s", name)
            continue

        func = get_indicator(name)
        new_columns = func(df, **params)
        for col_name, series in new_columns.items():
            df[col_name] = series

    return df


def _processed_csv_path(data_cfg):
    exchange_id = data_cfg["exchange"]
    symbol = data_cfg["symbol"].replace("/", "-")
    timeframe = data_cfg["timeframe"]
    return Path(data_cfg["processed_dir"]) / f"{exchange_id}_{symbol}_{timeframe}.csv"


def _synthetic_demo_df(rows=300):
    """Veri katmanı henüz çalıştırılmamışsa indikatörleri gösterebilmek için
    sahte (rastgele yürüyüş) bir OHLCV serisi üretir. Gerçek analiz için
    kullanılmamalı — sadece demo/duman testi amaçlıdır.
    """
    rng = np.random.default_rng(42)
    steps = rng.normal(loc=0, scale=50, size=rows)
    close = 30000 + np.cumsum(steps)
    close = np.clip(close, 1000, None)

    timestamps = pd.date_range("2024-01-01", periods=rows, freq="1h", tz="UTC")
    high = close + rng.uniform(0, 30, size=rows)
    low = close - rng.uniform(0, 30, size=rows)
    open_ = close + rng.uniform(-15, 15, size=rows)
    volume = rng.uniform(10, 100, size=rows)

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


def run(config=None, input_csv=None):
    config = config or load_config()
    data_cfg = config["data"]

    if input_csv is None:
        input_csv = _processed_csv_path(data_cfg)

    if Path(input_csv).exists():
        df = pd.read_csv(input_csv, parse_dates=["timestamp"])
        source = str(input_csv)
    else:
        logger.warning(
            "İşlenmiş veri bulunamadı (%s). Önce `python -m src.data.pipeline` "
            "çalıştırın. Şimdilik demo amaçlı sentetik veri kullanılıyor.",
            input_csv,
        )
        df = _synthetic_demo_df()
        source = "sentetik demo verisi (GERÇEK DEĞİL)"

    enriched = apply_indicators(df, config.get("indicators"))
    return enriched, source


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    df, source = run()

    print(f"Veri kaynağı: {source}")
    print(df.tail(10).to_string())
    print(f"\nToplam satır: {len(df)}")
    print(f"Sütunlar: {list(df.columns)}")


if __name__ == "__main__":
    main()
