"""ccxt tabanlı borsa OHLCV geçmiş veri istemcisi.

Varsayılan borsa OKX'tir (kullanıcı OKX üzerinden işlem yapıyor), ama
`exchange_id` parametresiyle ccxt'nin desteklediği herhangi bir borsaya
geçilebilir.
"""

import logging
import time

import ccxt

logger = logging.getLogger(__name__)


class ExchangeDataClient:
    """Belirli bir borsadan sayfalayarak (pagination) geçmiş OHLCV mumu çeker."""

    def __init__(self, exchange_id="okx", max_retries=5, retry_backoff_seconds=2, exchange=None):
        # `exchange` parametresi testlerde gerçek ağ çağrısı yapmadan sahte
        # (fake) bir borsa nesnesi enjekte edebilmek için var.
        if exchange is not None:
            self.exchange = exchange
        else:
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange = exchange_class({"enableRateLimit": True})

        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds

    def fetch_ohlcv_history(self, symbol, timeframe, since_ms, until_ms=None, limit=300):
        """`since_ms`'den `until_ms`'e (verilmezse şu ana) kadar OHLCV mumlarını çeker.

        Borsalar tek çağrıda sınırlı sayıda mum döner (limit), bu yüzden
        döndürülen son mumun zaman damgasından devam ederek sayfalama yapılır.
        """
        until_ms = until_ms if until_ms is not None else int(time.time() * 1000)
        timeframe_ms = self.exchange.parse_timeframe(timeframe) * 1000

        all_candles = []
        cursor = since_ms

        while cursor < until_ms:
            batch = self._fetch_with_retry(symbol, timeframe, cursor, limit)
            if not batch:
                break

            all_candles.extend(batch)
            last_ts = batch[-1][0]

            if last_ts < cursor:
                # Borsa beklenmedik/eski veri döndürdü, sonsuz döngüye girmeyelim.
                logger.warning("Borsa geriye dönük mum döndürdü, sayfalama durduruluyor.")
                break

            next_cursor = last_ts + timeframe_ms
            if next_cursor <= cursor:
                # İlerleme kaydedilemiyor, sonsuz döngüyü önle.
                break
            cursor = next_cursor

            if len(batch) < limit:
                # Borsa istenen limitten az mum döndürdüyse elindeki veri bitmiştir.
                break

        # Sayfalama sırasında aralığın dışına taşabilen mumları kırp.
        return [c for c in all_candles if since_ms <= c[0] < until_ms]

    def _fetch_with_retry(self, symbol, timeframe, since_ms, limit):
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
            except (ccxt.NetworkError, ccxt.ExchangeNotAvailable) as e:
                last_error = e
                wait_seconds = self.retry_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "Veri çekme hatası (deneme %d/%d): %s - %ss bekleniyor",
                    attempt,
                    self.max_retries,
                    e,
                    wait_seconds,
                )
                if attempt < self.max_retries:
                    time.sleep(wait_seconds)
        raise last_error
