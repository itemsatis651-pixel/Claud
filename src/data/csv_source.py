"""URL'den (örn. GitHub'da barındırılan) toplu geçmiş OHLCV verisi çeken istemci.

`ExchangeDataClient` ile aynı arayüzü (`fetch_ohlcv_history`) sağlar, böylece
`pipeline.py` hangi kaynağı kullandığını bilmek zorunda kalmaz — config'te
`data.source: csv_url` seçilince devreye girer.

Ne işe yarar: Borsa API'sine erişimin olmadığı ortamlarda (örn. bu geliştirme
sandbox'ı) veya büyük bir geçmiş veriyi tek seferde "bootstrap" etmek
istediğinizde kullanılır. Üretim / canlı kullanım için varsayılan kaynak yine
borsa API'sidir (`ExchangeDataClient`) — bu sadece bir alternatif/tamamlayıcı.
"""

import logging
from io import StringIO

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class CsvUrlDataClient:
    """Tek bir CSV dosyasını (URL'den) indirip standart OHLCV formatına çevirir.

    `column_map`: bizim standart isimlerimizi ("timestamp", "open", "high",
    "low", "close", "volume") kaynak CSV'nin gerçek sütun isimlerine eşler.
    Örn: {"timestamp": "UNIX_TIMESTAMP", "open": "OPEN", ...}
    """

    def __init__(self, url, column_map, timestamp_unit="s", timeout=60, session=None):
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = required - set(column_map.keys())
        if missing:
            raise ValueError(f"column_map şu anahtarları içermeli: {missing}")

        self.url = url
        self.column_map = column_map
        self.timestamp_unit = timestamp_unit
        self.timeout = timeout
        self._session = session or requests
        self._cached_df = None

    def _load(self):
        if self._cached_df is not None:
            return self._cached_df

        logger.info("CSV veri kaynağı indiriliyor: %s", self.url)
        response = self._session.get(self.url, timeout=self.timeout)
        response.raise_for_status()

        raw_df = pd.read_csv(StringIO(response.text))
        source_columns = list(self.column_map.values())
        missing = [col for col in source_columns if col not in raw_df.columns]
        if missing:
            raise ValueError(
                f"CSV'de beklenen sütunlar yok: {missing}. Mevcut sütunlar: {list(raw_df.columns)}"
            )

        renamed = raw_df[source_columns].rename(columns={v: k for k, v in self.column_map.items()})

        multiplier = 1000 if self.timestamp_unit == "s" else 1
        renamed["timestamp_ms"] = renamed["timestamp"].astype("int64") * multiplier
        renamed = renamed.sort_values("timestamp_ms").reset_index(drop=True)

        self._cached_df = renamed
        return renamed

    def fetch_ohlcv_history(self, symbol, timeframe, since_ms, until_ms=None, limit=None):
        """`ExchangeDataClient` ile aynı imza - `symbol`/`timeframe` bu kaynak
        için kullanılmaz (CSV tek bir sembol/periyoda ait kabul edilir), sadece
        arayüz uyumluluğu için burada duruyor."""
        df = self._load()
        mask = df["timestamp_ms"] >= since_ms
        if until_ms is not None:
            mask &= df["timestamp_ms"] < until_ms

        subset = df.loc[mask, ["timestamp_ms", "open", "high", "low", "close", "volume"]]
        return subset.values.tolist()
