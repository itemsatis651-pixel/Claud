# Backtest Katmanı (`src/backtest`)

Sinyal serisini (`AL`/`SAT`/`BEKLE`) gerçekçi bir işlem simülasyonuna çevirip
fee+slipaj dahil performans ölçen, yıllık ve piyasa rejimi bazlı dökümü
üreten katman.

## Dosyalar

- **`engine.py`** — `run_backtest()`: pozisyon durumu takipli (flat/long)
  simülasyon. **Bar X+1'in açılışında** işlem yapar (bar X'in kapanışından
  DEĞİL — look-ahead bias önleme, aşağıda detay), fee+slipaj uygular, tek
  pozisyon/uzun-only/tam-boyut varsayımıyla çalışır (kısmi pozisyon/stop-loss
  Adım 5'te).
- **`metrics.py`** — `compute_metrics()`: toplam getiri, CAGR, Sharpe,
  Sortino, maksimum drawdown, kazanma oranı, profit factor, vb.
  `segment_return_pct()`: equity curve'ün bir alt-aralığındaki getiri (yıllık/
  in-out-of-sample dökümü için kullanılır).
- **`regime.py`** — `classify_regime()`: SADECE fiyat verisinden, sabit bir
  kuralla (uzun vadeli SMA eğimi) piyasayı BOĞA/AYI/YATAY olarak sınıflandırır
  — tarihleri elle seçmenin (veri casusluğu) önüne geçmek için.
- **`pipeline.py`** — Her şeyi birleştirir: veri → indikatör → strateji →
  backtest → metrikler → yıllık/rejim dökümü → dürüst rapor.

## Kritik tasarım kararları

1. **Bar X+1'in açılışında işlem:** Sinyal bar X'in kapanışına bakılarak
   üretiliyor; gerçek hayatta bu bilgiyle en erken işlem yapılabilecek an bar
   X+1'in açılışıdır. Aynı barın kapanışından işlem yapmak (çok yaygın bir
   backtest hatası) imkansız bir zamanlama avantajı verir ve sonuçları
   olduğundan iyi gösterir.
2. **Tek, kesintisiz simülasyon:** Veri parçalara bölünüp ayrı ayrı simüle
   EDİLMİYOR. Yıllık ve rejim bazlı raporlar, TEK simülasyonun equity
   curve'ü/işlem listesi üzerine dilimleme yapılarak üretiliyor — aksi halde
   yıl/rejim sınırında açık pozisyonlar yapay şekilde kesilir/bozulur.
3. **Rejim → işlem eşleştirmesi:** Her tamamlanmış işlem, GİRİŞ barındaki
   rejime göre gruplanıyor. Bir işlem süresince rejim değişmiş olabilir (bu
   basit bir yaklaşım, dürüstçe not ediliyor).

## SONUÇLAR — dürüst rapor (referans veri: 2020-01-01 → 2026-09-13, 58.728 saatlik mum)

### Bulunan ve düzeltilen bir hata

İlk implementasyonda strateji parametreleri ("Turtle System 2" 55/20 gün +
200 günlük trend filtresi) **saate çevrilmeden** kullanılmıştı (55/20/200
SAAT). Bu haliyle backtest **-2.25% toplam getiri** (Buy&Hold: +977%),
Sharpe 0.15, profit factor ≈1.00 (neredeyse rastgele) verdi — whipsaw'a tam
anlamıyla açık, aşırı kısa vadeli bir sistem olmuştu. Hata fark edilip
saatlik karşılıklarıyla (×24) düzeltildi: `entry_period=1320` (55 gün),
`exit_period=480` (20 gün), `trend_filter_period=4800` (200 gün). **Bu bir
"backtest sonucuna göre parametre ayarlama" değil, bir birim dönüşüm
düzeltmesidir** — literatürdeki günlük sistemi doğru şekilde saatlik bara
uyarlamak. Aşağıdaki sonuçlar düzeltilmiş haliyledir.

### Genel sonuçlar (tek, kesintisiz simülasyon, fee %0.10 + slipaj %0.05 dahil)

| Metrik | Değer |
|---|---|
| Toplam getiri | **+644.69%** |
| Buy & Hold (aynı dönem) | +977.19% |
| CAGR | 34.94% |
| Sharpe (risksiz oran=0) | 1.04 |
| Sortino | 0.75 |
| Maksimum drawdown | **-33.49%** |
| İşlem sayısı | **16** (+ dönem sonunda 1 açık pozisyon) |
| Kazanma oranı | 62.5% |
| Ortalama kazanç / kayıp | +44.60% / -9.97% |
| Profit factor | 2.42 |

### Dürüst değerlendirme

- **Buy & Hold'u YENEMEDİ** (mutlak getiride): 644.69% vs 977.19%. Ancak
  maksimum drawdown çok daha düşük (-33.49% vs BTC'nin bu dönemde yaşadığı
  çok daha derin düşüşler, örn. 2022 ayı piyasasında %70+). Bu, klasik
  trend-takip ödünleşmesi: daha az mutlak getiri, çok daha az risk/stres.
  Hangisinin "daha iyi" olduğu kullanıcının risk toleransına bağlı — siz
  "hepsini raporla, tek öncelik seçme" dediniz, bu yüzden tercih size ait.
- **İşlem sayısı ÇOK KÜÇÜK (16):** Bu, güvenilir istatistiksel çıkarım için
  yetersiz bir örneklem. %62.5 kazanma oranı ve 2.42 profit factor birkaç
  büyük kazançlı işleme çok duyarlı olabilir (nitekim BOĞA rejimindeki 3
  işlem, toplam kârın büyük kısmını oluşturuyor - ortalama %114.8 getiri).
  Bu sonuçlara **yüksek güvenle** "bu strateji çalışıyor" denemez - küçük
  örneklem riski açık şekilde var.
- **2022'de tam sıfır getiri (0.00%):** Strateji muhtemelen 2022 ayı
  piyasasının (Terra/Luna, FTX çöküşü) büyük kısmında pozisyon dışında/nakit
  kalmış - bu trend-takip felsefesiyle tutarlı, olumlu bir gözlem, ama tek
  bir yılın tek bir gözlemi, genelleştirilemez.
- **In-sample (2020-2022) +340.33%, out-of-sample (2023-2026) +69.12%:**
  Yön aynı kaldı (negatife dönmedi) ama getiri büyüklüğü belirgin şekilde
  azaldı. Bu "ortalamaya dönüş" mü yoksa gerçekten daha az güçlü trend
  fırsatı mı belirsiz - kesin yorum yapmıyoruz.
- **Bu veri OKX'ten değil** (bkz. `src/data/README.md`) - gerçek OKX
  verisiyle tekrarlanmadan bu sonuçlara tam güvenilmemeli.
- **Fee/slipaj varsayımları basit/sabit** (%0.10 + %0.05) - gerçekte
  oynaklığa, emir büyüklüğüne, likiditeye göre değişir; büyük pozisyonlarda
  slipaj daha yüksek olabilir.
- **Risk yönetimi katmanı henüz yok** (Adım 5) - bu sonuçlar "tüm sermaye
  içeri/dışarı" varsayımıyla; stop-loss/pozisyon boyutlandırma eklenince
  sonuçlar (muhtemelen drawdown lehine, getiri aleyhine) değişecek.

### Yıllık dökümü

| Yıl | Getiri |
|---|---|
| 2020 | +150.58% |
| 2021 | +75.26% |
| 2022 | 0.00% |
| 2023 | +34.81% |
| 2024 | +42.18% |
| 2025 | -20.63% |
| 2026 (Eylül'e kadar) | +10.70% |

2025'te belirgin bir kayıp yılı var - bu da "her yıl kazandırır" beklentisine
karşı dengeli bir gözlem.

### Rejim bazlı dökümü (işlemler giriş rejimine göre)

| Rejim | İşlem | Kazanma oranı | Ort. getiri | Toplam PNL |
|---|---|---|---|---|
| BOĞA | 3 | %66.7 | +114.76% | 45.689 |
| YATAY | 11 | %54.5 | +2.43% | 6.664 |
| AYI | 1 | %100 | +10.02% | 4.411 |

Kâr büyük ölçüde az sayıda BOĞA rejimindeki büyük trend yakalamasından
geliyor - beklenen trend-takip profili, ama örneklem (özellikle AYI'da n=1)
çok küçük.

## Overfitting'e karşı önlemler (özet)

- Parametreler literatürden alındı, bu veri setine optimize edilmedi (sadece
  birim hatası düzeltildi - yukarıda açıklandı).
- Rejim sınıflandırması tarihleri elle seçmek yerine sabit bir kurala
  dayanıyor.
- Look-ahead bias hem strateji katmanında (önceki bar kanalı) hem backtest
  motorunda (sonraki bar açılışı) önlendi.
- In-sample/out-of-sample ayrımı raporlanıyor (ama not: parametre fit
  edilmediği için bu "overfitting önleme" değil, "zaman içi tutarlılık
  kontrolü" amaçlı).

## Kullanım

```bash
python -m src.backtest.pipeline
```

## Test

```bash
python -m pytest tests/test_backtest_engine.py tests/test_backtest_metrics.py tests/test_backtest_regime.py -v
```

Testler motor mantığını (look-ahead önleme, fee/slipaj hesabı, no-op
davranışları), metrik formüllerini ve rejim sınıflandırmasını kontrollü
senaryolarla doğrular - gerçek veri gerektirmez.
