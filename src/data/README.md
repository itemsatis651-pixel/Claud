# Veri Katmanı (`src/data`)

BTC OHLCV (mum) verisini borsadan çekip temizleyen katman. Sonraki tüm
katmanlar (indikatörler, strateji, backtest) bu modülün ürettiği temiz
DataFrame üzerine kurulacak.

## Dosyalar

- **`exchange_client.py`** — `ExchangeDataClient`: ccxt üzerinden (varsayılan
  borsa: OKX) geçmiş OHLCV mumlarını sayfalayarak (pagination) çeker.
  Geçici ağ hatalarında exponential backoff ile yeniden dener
  (`max_retries`, `retry_backoff_seconds`). Testlerde gerçek ağ çağrısı
  yapmadan sahte bir borsa nesnesi enjekte edilebilmesi için `exchange=`
  parametresi alır.

- **`clean.py`** — Saf (network'e dokunmayan) temizleme fonksiyonları:
  - `ohlcv_list_to_df`: ccxt'nin ham liste formatını DataFrame'e çevirir.
  - `clean_ohlcv`: kopya zaman damgalarını atar, zamana göre sıralar, NaN
    satırları atar, mantıksız OHLC ilişkilerini (örn. `high < low`,
    negatif hacim) atar, ve bir **kalite raporu** döner.
  - `detect_gaps`: beklenen mum aralığına göre eksik mumları (zaman
    boşluklarını) tespit eder — **silmez, sadece raporlar**. Eksik mumları
    doldurmak (interpolasyon vb.) bilinçli bir strateji kararı olduğu için
    şu an otomatik yapılmıyor.

- **`csv_source.py`** — `CsvUrlDataClient`: `ExchangeDataClient` ile aynı
  arayüzü sağlayan alternatif bir veri kaynağı. Bir URL'deki CSV dosyasını
  indirip standart OHLCV formatına çevirir. Borsa API'sine erişimin olmadığı
  ortamlarda (bkz. aşağıdaki "Bilinen kısıtlamalar") veya büyük bir geçmişi
  tek seferde bootstrap etmek isterken kullanılır. `config.data.source:
  csv_url` ile devreye girer; varsayılan hâlâ `exchange` (OKX)'tir.

- **`pipeline.py`** — Her şeyi birleştiren orkestrasyon katmanı:
  1. `config/settings.yaml`'ı okur.
  2. Daha önce cache'lenmiş veri varsa (`data/raw/*.parquet`) sadece son
     mumdan itibaren eksik veriyi çeker (incremental fetch).
  3. Yeni veriyi temizler, cache'i ve `data/processed/*.csv` kopyasını
     günceller.
  4. Kalite raporunu döner/yazdırır.

## Kullanım

```bash
python -m src.data.pipeline
```

Config'i değiştirmeden farklı bir dosya ile çalıştırmak isterseniz
`fetch_and_clean(config=...)` fonksiyonunu kendi scriptinizden çağırabilirsiniz.

## Config anahtarları (`config/settings.yaml` -> `data:`)

| Anahtar | Açıklama |
|---|---|
| `exchange` | ccxt borsa id'si (`okx`) |
| `symbol` | İşlem çifti (`BTC/USDT`) |
| `timeframe` | Mum periyodu (`1h`) |
| `history_start` | Geçmişe ne kadar gidileceği (ISO 8601, UTC) |
| `cache_dir` | Ham/temizlenmiş veri cache'i (parquet, git'e girmez) |
| `processed_dir` | İnsan tarafından incelenebilir çıktı (csv, git'e girmez) |
| `max_retries`, `retry_backoff_seconds` | Ağ hatası yeniden deneme ayarları |
| `source` | `exchange` (varsayılan, OKX/ccxt) veya `csv_url` (toplu CSV bootstrap) |
| `csv_url.*` | `source: csv_url` iken kullanılan URL, sütun eşleme, zaman damgası birimi |

## Bilinen kısıtlamalar ve dürüst notlar

- **OKX'in geçmiş veri derinliği:** OKX'in genel `candles` endpoint'i son
  birkaç yüz mumla sınırlıdır; daha eskiye gitmek için ccxt'nin
  `history-candles` endpoint'ine geçmesi gerekebilir. Borsa çok eski tarihe
  (örn. 2020) hiç veri döndürmüyorsa, `pipeline.py` çalıştırıldığında
  rapordaki `start` alanına bakıp gerçekte ne kadar geriye gidildiğini
  kontrol edin — sessizce eksik veri üretmez, sadece elde ettiği kadarını
  döner.

- **Bu geliştirme ortamının ağ kısıtlaması:** Bu Claude Code oturumu,
  organizasyonun egress (giden ağ) politikası gereği borsa API'lerine
  erişemiyor — sadece OKX değil, Binance (API ve `data.binance.vision`
  statik veri sunucusu), Kraken, CoinGecko, Coinbase, CryptoCompare, Yahoo
  Finance de denendi, hepsi 403 ile engellendi (organizasyon seviyesinde
  "finans/borsa" kategorisi engellenmiş görünüyor). Bu yüzden **canlı OKX
  veri çekme bu ortamda test edilemedi**. `ExchangeDataClient`'ın mantığı
  (sayfalama, retry, cache/incremental fetch) sahte (fake/mock) borsa
  nesneleriyle 13 birim testle doğrulandı — ama gerçek OKX API'sinin
  davranışıyla %100 aynı olacağının garantisi yok. **Lütfen
  `python -m src.data.pipeline` komutunu kendi makinenizde (ağ kısıtı
  olmayan bir ortamda) çalıştırıp gerçek veri çekildiğini doğrulayın.**

- **Sandbox'ta gerçek veriyle geliştirme için geçici çözüm (`csv_url`
  kaynağı):** GitHub'a (raw/media.githubusercontent.com) bu ortamdan
  erişilebildiği için, geliştirme ve test amaçlı MIT lisanslı, günlük
  güncellenen bir BTC saatlik OHLCV veri setini (kaynak:
  [github.com/mouadja02/bitcoin-technical-indicators-dataset](https://github.com/mouadja02/bitcoin-technical-indicators-dataset))
  `config/settings.yaml`'a `csv_url` seçeneği olarak ekledik. Bunu
  `data.source: csv_url` yaparak (geçici olarak) çalıştırdık ve şu sonucu
  aldık: **2020-01-01 → 2026-09-13 arası 58.728 saatlik mum, sadece 1 eksik
  mum (gap) ve 1 geçersiz satır** — 6 yıllık veri için çok temiz.
  Sonuç `data/raw/github_btc_reference_BTC-USDT_1h.parquet` ve
  `data/processed/github_btc_reference_BTC-USDT_1h.csv` olarak (cache
  dosya adı bilerek `okx_...` değil `github_btc_reference_...` — gerçek
  OKX verisiyle karışmasın diye) kaydedildi ve indikatör katmanı bu
  veriyle test edildi, sonuçlar sağlıklı çıktı.

  **Dürüst uyarı:** Bu veri OKX'ten değil, farklı bir kaynaktan (muhtemelen
  Binance/Coinbase agregasyonu) geliyor. BTC/USDT fiyatları borsalar arası
  çok yakın olsa da (arbitraj sayesinde) birebir aynı değildir. Bu veri
  **strateji/backtest mantığını geliştirmek ve doğrulamak için** kullanışlı,
  ama **nihai/üretim backtest'i mutlaka gerçek OKX verisiyle
  (`source: exchange`, kendi makinenizde) tekrarlanmalı** — sonuçlar
  küçük farklılıklar gösterebilir. Varsayılan config hâlâ `source: exchange`
  (OKX) olarak bırakıldı, `csv_url` sadece bir yardımcı/opsiyonel özellik.
- **Eksik mumlar otomatik doldurulmuyor:** `detect_gaps` sadece raporlar.
  İndikatör/strateji katmanında eksik mumların nasıl ele alınacağına
  (örn. forward-fill mi, o dönemi backtest'ten hariç mi tutacağız) birlikte
  karar vereceğiz.

## Tek başına test

```bash
python -m pytest tests/test_clean.py tests/test_exchange_client.py tests/test_pipeline.py -v
```
