"""Veri katmanını uçtan uca çalıştıran orkestrasyon modülü.

Akış: config oku -> cache'den kaldığı yerden devam et -> borsadan eksik
mumları çek -> temizle -> cache'i (parquet) ve okunabilir bir kopyayı (csv)
güncelle -> kalite raporu döndür.

Tek başına çalıştırma: `python -m src.data.pipeline`
"""

import logging
from pathlib import Path

import pandas as pd

from src.data.clean import OHLCV_COLUMNS, clean_ohlcv, ohlcv_list_to_df
from src.data.csv_source import CsvUrlDataClient
from src.data.exchange_client import ExchangeDataClient
from src.utils.config import load_config

logger = logging.getLogger(__name__)


def _cache_label(data_cfg):
    """Cache dosya adında kullanılacak kaynak etiketi.

    `source: csv_url` iken `exchange` alanıyla (gerçek işlem borsası) karışmasın
    diye ayrı bir etiket kullanılır - aksi halde "okx" ile cache'lenmiş bir
    dosyanın aslında GitHub'dan gelen bir CSV mi yoksa gerçek OKX API'sinden mi
    geldiği belirsizleşir.
    """
    if data_cfg.get("source", "exchange") == "csv_url":
        return data_cfg["csv_url"].get("label", "csv_source")
    return data_cfg["exchange"]


def _build_client(data_cfg):
    if data_cfg.get("source", "exchange") == "csv_url":
        csv_cfg = data_cfg["csv_url"]
        return CsvUrlDataClient(
            url=csv_cfg["url"],
            column_map=csv_cfg["column_map"],
            timestamp_unit=csv_cfg.get("timestamp_unit", "s"),
        )
    return ExchangeDataClient(
        exchange_id=data_cfg["exchange"],
        max_retries=data_cfg.get("max_retries", 5),
        retry_backoff_seconds=data_cfg.get("retry_backoff_seconds", 2),
    )


def _cache_path(cache_dir, source_label, symbol, timeframe):
    safe_symbol = symbol.replace("/", "-")
    return Path(cache_dir) / f"{source_label}_{safe_symbol}_{timeframe}.parquet"


def fetch_and_clean(config=None, exchange_client=None):
    """Config'e göre veriyi çeker (cache'den devam ederek), temizler, kaydeder.

    `exchange_client` parametresi testlerde gerçek ağ çağrısı yapmayan sahte
    bir istemci enjekte edebilmek için var.
    """
    config = config or load_config()
    data_cfg = config["data"]

    source_label = _cache_label(data_cfg)
    symbol = data_cfg["symbol"]
    timeframe = data_cfg["timeframe"]
    history_start = pd.Timestamp(data_cfg["history_start"])
    if history_start.tzinfo is None:
        history_start = history_start.tz_localize("UTC")
    else:
        history_start = history_start.tz_convert("UTC")

    cache_dir = Path(data_cfg["cache_dir"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(cache_dir, source_label, symbol, timeframe)

    if cache_file.exists():
        cached_df = pd.read_parquet(cache_file)
        cached_df["timestamp"] = pd.to_datetime(cached_df["timestamp"], utc=True)
    else:
        cached_df = pd.DataFrame(columns=OHLCV_COLUMNS)

    since_ms = int(history_start.timestamp() * 1000)
    if len(cached_df) > 0:
        last_ts = cached_df["timestamp"].max()
        since_ms = max(since_ms, int(last_ts.timestamp() * 1000) + 1)
        logger.info("Cache bulundu: %d satır, %s tarihinden itibaren devam ediliyor", len(cached_df), last_ts)

    client = exchange_client or _build_client(data_cfg)

    raw_candles = client.fetch_ohlcv_history(symbol, timeframe, since_ms)
    new_df = ohlcv_list_to_df(raw_candles) if raw_candles else pd.DataFrame(columns=OHLCV_COLUMNS)

    combined = pd.concat([cached_df, new_df], ignore_index=True)
    cleaned_df, report = clean_ohlcv(combined, timeframe)

    cleaned_df.to_parquet(cache_file, index=False)

    processed_dir = Path(data_cfg["processed_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    processed_file = processed_dir / cache_file.name.replace(".parquet", ".csv")
    cleaned_df.to_csv(processed_file, index=False)

    report["new_candles_fetched"] = len(new_df)
    report["cache_file"] = str(cache_file)
    report["processed_file"] = str(processed_file)
    return cleaned_df, report


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    df, report = fetch_and_clean()

    print("=== Veri Özeti ===")
    for key, value in report.items():
        if key == "gaps":
            continue
        print(f"{key}: {value}")

    if report.get("gaps"):
        print(f"\nUyarı: {len(report['gaps'])} zaman boşluğu bulundu (ilk 5 gösteriliyor):")
        for gap in report["gaps"][:5]:
            print(f"  {gap['after']} -> {gap['before']} ({gap['missing_candles']} mum eksik)")

    return df, report


if __name__ == "__main__":
    main()
