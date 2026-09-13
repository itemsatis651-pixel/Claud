# İndikatör Katmanı (`src/indicators`)

Ham OHLCV DataFrame'ine klasik teknik indikatör sütunları ekleyen, plug-in
tarzı bir katman. Sonraki adımda (strateji) bu sütunlar üzerinden kural
tabanlı al/sat sinyalleri üretilecek.

## Dosyalar

- **`registry.py`** — İndikatörleri isimle kaydeden/çağıran merkezi kayıt
  defteri (`@register_indicator("isim")`). Config'teki isim ile kodun
  birbirine sıkı bağlı olmasını önler.
- **`trend.py`** — `sma` (basit hareketli ortalama), `ema` (üstel hareketli
  ortalama).
- **`momentum.py`** — `rsi` (Wilder yöntemi), `macd` (hızlı/yavaş EMA farkı +
  sinyal hattı + histogram).
- **`volatility.py`** — `bollinger` (orta bant = SMA, üst/alt bant = ±N
  standart sapma).
- **`trend.py`** (`donchian`) — Donchian Channel: son N bardaki en yüksek
  high / en düşük low. Breakout/trend-takip stratejilerinin temel yapı taşı.
- **`pipeline.py`** — `apply_indicators(df, indicators_config)`: config'teki
  aktif indikatörleri df'e uygular. `run()`: `data/processed/*.csv`'yi okuyup
  indikatörleri ekler; dosya yoksa (henüz `src.data.pipeline`
  çalıştırılmadıysa) **sentetik demo verisiyle** çalışır — bu veri gerçek
  değildir, sadece modülün çalıştığını göstermek içindir.

## Kullanım

```bash
python -m src.indicators.pipeline
```

Kendi kodunuzdan:

```python
from src.indicators.pipeline import apply_indicators
df_with_indicators = apply_indicators(df, config["indicators"])
```

## Config (`config/settings.yaml` -> `indicators:`)

Her indikatör kendi alt bloğunda parametrelerini alır. `enabled: false` ile
bir indikatörü koddan silmeden kapatabilirsiniz:

```yaml
indicators:
  sma:
    enabled: true
    windows: [20, 50, 200]   # her window için ayrı sütun: sma_20, sma_50, sma_200
  rsi:
    enabled: true
    period: 14
```

## Yeni bir indikatör eklemek (plug-in mimarisi)

1. `src/indicators/` altına (veya var olan bir dosyaya) bir fonksiyon yazın.
   İmza: `def my_indicator(df, **params) -> dict[str, pd.Series]`.
2. `@register_indicator("my_indicator")` ile işaretleyin.
3. Yeni bir dosyaysa `pipeline.py`'nin en üstüne
   `import src.indicators.my_module  # noqa: F401` satırını ekleyin (var olan
   dosyaya eklediyseniz bu adım gerekmez).
4. `config/settings.yaml` -> `indicators:` altına `my_indicator: {...}` ekleyin.

Kod tabanının geri kalanı hiçbir şey değiştirmeden yeni indikatörü otomatik
kullanır.

## Neden hazır kütüphane (pandas-ta vb.) yerine kendi formüllerimiz?

Overfitting ve backtest doğruluğu konusunda tam şeffaflık istiyoruz — her
formülün ne yaptığını satır satır görebilmek, "kara kutu" bir kütüphaneye
güvenmemek için indikatörler pandas/numpy ile sıfırdan yazıldı. Formüller
standart tanımları takip eder (RSI: Wilder'ın orijinal üstel düzeltmesi,
MACD: 12/26/9 varsayılan EMA farkı, Bollinger: 20 periyot ±2 std).

## Test

```bash
python -m pytest tests/test_indicators.py -v
```

Testler bilinen matematiksel özellikleri doğrular (örn. sürekli artan bir
seride RSI'ın 100'e yakınsaması, sabit fiyatta Bollinger bantlarının
fiyata çökmesi) — gerçek piyasa verisi gerektirmez.
