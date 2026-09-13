# Strateji Katmanı (`src/strategies`)

İndikatörlerle zenginleştirilmiş OHLCV verisine bakıp net **AL/SAT/BEKLE**
sinyali + bir **skor** + bir **gerekçe metni** üreten, plug-in tarzı kural
tabanlı strateji katmanı.

## Ana strateji: Donchian Channel Breakout (`donchian_breakout`)

### Neden bu strateji seçildi

İlk halde MACD+Stokastik ile başlanmıştı, ama kullanıcı bunun kendi rastgele
fikri olduğunu, gerçek araştırmaya dayalı bir seçim istediğini belirtti.
Bunun üzerine BTC'ye özel akademik/kantitatif araştırma yapıldı. Birden
fazla bağımsız kaynak aynı sonuca işaret ediyor:

> **BTC güçlü ve kalıcı trendler sergiliyor; trend-takip/momentum
> stratejileri mean-reversion'dan belirgin şekilde daha iyi ve daha
> dayanıklı (out-of-sample'da bile) çalışıyor.**

Kaynaklar:
- [Grayscale Research — "The Trend is Your Friend: Managing Bitcoin's Volatility with Momentum Signals"](https://research.grayscale.com/reports/the-trend-is-your-friend-managing-bitcoins-volatility-with-momentum-signals)
- [Rohrbach, Suremann, Osterrieder (SSRN) — "Momentum and Trend Following Trading Strategies for Currencies and Bitcoin"](https://papers.ssrn.com/Sol3/Delivery.cfm/SSRN_ID2949379_code2672176.pdf?abstractid=2949379)
- [QuantPedia — "Revisiting Trend-following and Mean-reversion Strategies in Bitcoin"](https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/) — Kasım 2015-Ağustos 2024 out-of-sample testinde "MAX" (breakout tarzı trend) stratejisi sağlam kalırken "MIN" (mean-reversion) stratejisi out-of-sample'da zayıfladı.
- Çeşitli bağımsız backtestler (Coinquant, TrendSpider, TheTradingMuse):
  Donchian Channel Breakout "70 yıldır emtia/döviz/hisse senedi
  piyasalarında test edilmiş en basit ve en dayanıklı trend-takip
  sistemlerinden biri".

Donchian Channel Breakout'un seçilme sebebi: yukarıdaki kanıtlarla en
tutarlı, EN AZ parametreli (2-3 parametre), en şeffaf mantığa sahip sistem
olması — "basit, kural tabanlı strateji" hedefiyle de örtüşüyor.

### Strateji mantığı

- **AL (giriş):** Kapanış, `entry_period` (varsayılan 55) barlık Donchian
  üst bandını — **bir önceki bara göre** — yukarı kırarsa VE kapanış uzun
  vadeli trend filtresinin (`trend_filter_period`, varsayılan SMA-200)
  üzerindeyse.
- **SAT (çıkış):** Kapanış, `exit_period` (varsayılan 20, girişten daha kısa)
  barlık Donchian alt bandını aşağı kırarsa — trend filtresinden bağımsız
  (çıkış sinyalleri girişten daha "gevşek" tutulur, standart risk yönetimi
  prensibi: kayıpları hızlı kes).
- **BEKLE:** diğer durumlar.
- **Look-ahead bias notu:** Kıyaslama her zaman **bir önceki barda biten**
  kanala göre yapılır (`shift(1)`) — aksi halde bugünün kanalı zaten bugünün
  kendi high/low'unu içerdiği için karşılaştırma anlamsızlaşır/yanıltıcı
  olurdu. Bu tür ince hatalar backtest'i gerçekte olduğundan çok daha iyi
  gösterebilir (klasik overfitting/lookahead tuzağı) — bilinçli olarak
  önlendi.

### Parametreler hakkında dürüstlük notu

`entry_period=55`, `exit_period=20` klasik "Turtle Trading System 2"
parametreleridir — orijinali **günlük** barlar için tasarlanmıştır. Burada
**saatlik** barlara uygulanıyor (55 saat ≈ 2.3 gün), bu birebir aynı "kaç
günlük fiyat hareketi" ölçeğini korumaz. Bu parametreler **bu veri setine
göre optimize edilmedi** (overfitting'den bilinçli kaçınma) — literatürden
alınan başlangıç noktaları. Adım 4'teki walk-forward backtest'te bu haliyle
test edilecek; sonuç kötüyse parametre taraması yapmak yerine önce zaman
dilimi/temel mantığı sorgulanacak.

### Bilinen zayıflık (araştırmadan, dürüstçe)

Breakout sistemleri yatay/choppy piyasalarda çok sayıda yanlış sinyal
(whipsaw) üretir, tipik kazanma oranı düşüktür (~%30-45) — kazanan
işlemlerin büyüklüğü kaybedenlerin sayısını telafi eder. Bu yüzden walk-
forward testte rejim bazlı (boğa/ayı/yatay) ayrı sonuç raporlanacak.

### Gerçek veriyle ön izleme (HENÜZ BACKTEST DEĞİL)

Referans veri setinde (2020-01-01 → 2026-09-13, 58.728 saatlik mum):

| Sinyal | Adet |
|---|---|
| BEKLE | 54.879 |
| SAT | 2.337 |
| AL | 1.512 |

**Önemli tasarım notu — bu sayılar "işlem sayısı" değildir:** Bu katman her
barı bağımsız olarak değerlendirir ("bu barda breakout koşulu sağlanıyor
mu?"), pozisyon durumunu (şu an pozisyondayım/değilim) takip etmez — bu
bilinçli bir katmanlama: sinyal üretimi ile pozisyon yönetimi ayrı
sorumluluklar. Güçlü bir yükseliş trendinde fiyat 55-bar zirvesini defalarca
kırabilir (her biri ayrı bir AL sinyali üretir), ama gerçek bir sistemde
zaten pozisyondaysanız bu sinyaller no-op'tur. **Gerçek işlem sayısı**
(sadece pozisyon dışıyken AL, pozisyon içindeyken SAT) adım 4'teki backtest
motorunda ortaya çıkacak — muhtemelen bu ham sayılardan çok daha az.
SAT'ın AL'den fazla olması da (2337 vs 1512) araştırmada belirtilen whipsaw
eğilimiyle tutarlı (çıkış filtresiz, sık tetikleniyor) — backtest'te bunun
gerçek P&L'e etkisini (çok sayıda küçük zararlı çıkış mı, yoksa zararsız
no-op'lar mı) göreceğiz.

## Alternatif: MACD + Stokastik (`macd_stochastic`)

Önceki iterasyonda (araştırma öncesi) uygulanan strateji hâlâ kayıtlı ve
kullanılabilir durumda (plug-in mimarisi sayesinde) — `config.strategy.active`
değiştirilerek karşılaştırma yapılabilir. Detaylar için dosyanın kendisine
(`macd_stochastic.py`) bakın. Trend filtresi + zamanlama tetikleyicisi olarak
makul bir yaklaşım olsa da, Donchian Breakout kadar güçlü/doğrudan BTC'ye
özel araştırma desteği yok — bu yüzden ana strateji olarak seçilmedi.

## Config (`config/settings.yaml` -> `strategy:`)

```yaml
strategy:
  active: donchian_breakout
  donchian_breakout:
    entry_period: 55      # indicators.donchian.periods ile eşleşmeli
    exit_period: 20        # indicators.donchian.periods ile eşleşmeli
    trend_filter_period: 200   # indicators.sma.windows ile eşleşmeli
```

## Kullanım

```bash
python -m src.strategies.pipeline
```

## Yeni bir strateji eklemek (plug-in mimarisi)

1. `src/strategies/` altına bir fonksiyon yazın. İmza:
   `def my_strategy(df, **params) -> pd.DataFrame` — `signal`, `signal_score`,
   `signal_reasons` sütunlarını ekleyip df'i döndürmeli.
2. `@register_strategy("my_strategy")` ile işaretleyin.
3. `pipeline.py`'nin en üstüne `import src.strategies.my_module  # noqa: F401`
   ekleyin.
4. `config/settings.yaml` -> `strategy.active: my_strategy` yapın ve kendi
   parametre bloğunuzu ekleyin.

## Sıradaki adım: Smart Money Concept

Kullanıcıyla üzerinde anlaşıldığı gibi, Smart Money Concept (order block /
BOS-CHoCH / FVG) katmanı bu temel doğrulandıktan sonra üçüncü bir confluence
bileşeni olarak eklenecek.

## Test

```bash
python -m pytest tests/test_donchian_breakout.py tests/test_strategies.py -v
```

Testler strateji mantığını (AL/SAT/BEKLE kararları, look-ahead bias'tan
kaçınma, trend filtresi, eksik sütunda hata verme) kontrollü senaryolarla
doğrular — gerçek veri gerektirmez.
