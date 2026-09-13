# Strateji Katmanı (`src/strategies`)

İndikatörlerle zenginleştirilmiş OHLCV verisine bakıp net **AL/SAT/BEKLE**
sinyali + bir **skor** + bir **gerekçe metni** üreten, plug-in tarzı kural
tabanlı strateji katmanı.

## Dosyalar

- **`registry.py`** — İndikatör katmanındakiyle aynı desen:
  `@register_strategy("isim")` ile kayıt, `config.strategy.active` ile seçim.
- **`macd_stochastic.py`** — İlk (temel) strateji: MACD + Stokastik
  confluence.
- **`pipeline.py`** — `apply_strategy(df, strategy_config)`: config'teki
  aktif stratejiyi uygular. `run()`: veriyi çeker → indikatörleri hesaplar →
  stratejiyi uygular, hepsini tek çağrıda yapar.

## MACD + Stokastik stratejisi — mantık

- **Trend filtresi (MACD):** histogram > 0 → yukarı momentum, < 0 → aşağı
  momentum.
- **Zamanlama tetikleyicisi (Stokastik):** %K'nın %D'yi **aşırı satım**
  bölgesinden (`%D < oversold`, varsayılan 20) yukarı kesmesi = alım tetiği;
  **aşırı alım** bölgesinden (`%D > overbought`, varsayılan 80) aşağı
  kesmesi = satım tetiği.
- **Confluence:** Trend filtresi ve tetikleyici aynı yönde ise **AL**/**SAT**;
  aksi halde **BEKLE**.
- **Skor:** MACD bileşeni (+1/-1/0) + Stokastik bileşeni (+1/-1/0), toplam
  -2..+2 arası (`signal_score` sütunu).
- **Gerekçe:** Hangi koşulların tetiklendiğini anlatan okunabilir metin
  (`signal_reasons` sütunu) — "net sinyal + arkasında skor/gerekçe" isteğini
  karşılamak için.

Bu strateji **bilinçli olarak basit** tutuldu ("karmaşık ML modeline
geçmeden önce basit kural tabanlı strateji" hedefiyle). **Smart Money
Concept** (order block / BOS-CHoCH / FVG) katmanı, bu temel doğrulandıktan
sonra ayrı bir confluence bileşeni olarak eklenecek (kullanıcıyla üzerinde
anlaşıldığı gibi — kapsamı ve nasıl birleştirileceği o adımda netleştirilecek).

## Config (`config/settings.yaml` -> `strategy:`)

```yaml
strategy:
  active: macd_stochastic
  macd_stochastic:
    macd_prefix: macd_12_26_9      # indicators.macd parametreleriyle eşleşmeli
    stoch_prefix: stoch_14_3_3     # indicators.stochastic parametreleriyle eşleşmeli
    oversold: 20
    overbought: 80
```

`macd_prefix`/`stoch_prefix` alanları, indikatör sütun isimlerinin
parametrelere göre değiştiğini (`macd_{fast}_{slow}_{signal}_hist` gibi)
hesaba katar — indikatör parametrelerini değiştirirseniz burayı da
güncellemeniz gerekir, aksi halde strateji `KeyError` fırlatır (sessizce
yanlış sütuna bakmak yerine).

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

## Gerçek veriyle sonuç (dürüst ön izleme — bu henüz backtest DEĞİL)

Referans veri setinde (2020-01-01 → 2026-09-13, 58.728 saatlik mum, bkz.
`src/data/README.md`) çalıştırıldığında:

| Sinyal | Adet |
|---|---|
| BEKLE | 58.572 |
| SAT | 110 |
| AL | 46 |

**Bunun ne anlama geldiği konusunda dürüst olmak gerekirse:**
- Aynı bar üzerinde katı confluence şartı arandığı için sinyal sıklığı
  düşük (~6.7 yılda 156 sinyal, yılda ~23) — bu bilinçli bir tercih (daha
  az ama daha "temiz" sinyal), ama backtest'te yeterli istatistiksel
  anlamlılık için işlem sayısının yeterli olup olmadığını sorgulayacağız.
- AL (46) ve SAT (110) sayıları arasındaki asimetri şu an **açıklanmadı** —
  piyasanın bu dönemde daha sık/keskin düşüşler yaşamasından mı, yoksa
  stratejinin yapısal bir yanlılığından mı kaynaklanıyor, bunu adım 4'teki
  backtest'te (özellikle farklı piyasa rejimlerinde ayrı test ederek)
  inceleyeceğiz.
- **Bu tablo sadece "kaç kere sinyal üretildi" gösteriyor — hangi
  sinyallerin kârlı olduğu, ne kadar kazandırdığı/kaybettirdiği HENÜZ
  BİLİNMİYOR.** Bunun için fee/slipaj dahil gerçekçi bir backtest motoru
  gerekiyor (adım 4). Şu anki sonuçlardan "bu strateji iyi/kötü" sonucu
  çıkarmak erken ve yanıltıcı olur.

## Test

```bash
python -m pytest tests/test_strategies.py -v
```

Testler strateji mantığını (AL/SAT/BEKLE kararları, skor hesabı, eksik
sütunda hata verme) kontrollü senaryolarla doğrular — gerçek veri
gerektirmez.
