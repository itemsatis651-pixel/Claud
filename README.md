# BTC Al/Sat Sinyal ve Backtest Sistemi

BTC için kural tabanlı al/sat sinyalleri üreten, gerçekçi (fee + slipaj
dahil) walk-forward backtest yapabilen, kişisel araştırma/analiz amaçlı
modüler bir sistem.

**Bu bir yatırım tavsiyesi aracı değildir.** Backtest sonuçları geçmiş
performansı gösterir; gelecekte tekrarlanacağının garantisi yoktur. Her
adımda overfitting riskine karşı dürüst bir değerlendirme yapılacak.

## ÖNEMLİ - Proje TradingView/Pine Script'e taşındı

Adım 4'ten sonra (backtest motoru) Python tarafında veri erişimi bu
geliştirme ortamında sürekli sürtünme yarattığı ve Smart Money Concept gibi
görsel kavramları TradingView'de doğrulamanın çok daha pratik olduğu
görüldüğü için, **aktif geliştirme artık `pinescript/` klasöründe (Pine
Script v6, TradingView)** devam ediyor — detaylar `pinescript/README.md`'de.
Python tarafı (`src/`, `config/`, `tests/` — aşağıda anlatılan Adım 1-4)
SİLİNMEDİ, repo'da referans/yedek olarak duruyor ve çalışır durumda
(64 test geçiyor), ama üzerinde aktif geliştirme yapılmıyor.

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Proje yapısı

```
config/
  settings.yaml       # Tüm ayarlar burada — kod değiştirmeden davranışı değiştirin
data/
  raw/                # Ham/temizlenmiş veri cache'i (parquet, git'e girmez)
  processed/          # İnsan tarafından incelenebilir çıktı (csv, git'e girmez)
src/
  utils/              # Ortak yardımcılar (config okuma vb.)
  data/               # Veri çekme ve temizleme katmanı (bkz. src/data/README.md)
  indicators/         # Teknik indikatörler, plug-in mimarisi (bkz. src/indicators/README.md)
  strategies/         # Kural tabanlı stratejiler, plug-in mimarisi (bkz. src/strategies/README.md)
  backtest/           # Backtest motoru, fee/slipaj, rejim/yıllık dökümü (bkz. src/backtest/README.md)
  risk/               # (sonraki adım) Pozisyon boyutlandırma, stop-loss, kayıp limitleri
  reporting/          # (sonraki adım) Equity curve, drawdown, işlem istatistikleri
tests/                # Her modül için birim testler
```

Her alt modülün kendi `README.md`'si var — aylar sonra geri dönüldüğünde
"bu modül ne yapıyordu" sorusuna hızlı cevap vermesi için.

## Mevcut durum (Adım 4/6: Backtest motoru tamamlandı)

**Adım 1 — Veri Katmanı** (`src/data`): OKX'ten (kullanıcının işlem yaptığı
borsa) 1 saatlik BTC/USDT mumlarını çeker, temizler (kopya/eksik/mantıksız
mum tespiti), zaman boşluklarını raporlar, incremental cache ile tekrar
çalıştırıldığında sadece eksik veriyi çeker.

```bash
python -m src.data.pipeline
```

**Önemli:** Bu geliştirme ortamının ağ politikası **her türlü dış piyasa
verisi API'sine** erişimi engelliyor (sadece OKX değil — Binance, Kraken,
CoinGecko, Coinbase, Yahoo Finance de denendi, hepsi aynı şekilde
engellendi). Bu yüzden canlı OKX veri çekme burada test edilemedi; mantık
mock veriyle birim testlerle doğrulandı (detaylar `src/data/README.md`'de).
Komutu kendi makinenizde çalıştırıp gerçek veri çekildiğini teyit edin.

**Sandbox'ta geliştirme için:** GitHub'a bu ortamdan erişilebildiğinden,
`data.source: csv_url` ile MIT lisanslı, gerçek ve güncel (2020-01-01 →
bugün, 58.728 saatlik mum, sadece 1 gap) bir BTC referans veri seti
bootstrap edildi (`data/raw/github_btc_reference_*`). Bu **OKX verisi
değil** — strateji/backtest geliştirmeyi gerçek fiyat hareketleriyle test
edebilmek için geçici bir yardımcı. Detaylar ve dürüst uyarı
`src/data/README.md`'de.

**Adım 2 — İndikatörler** (`src/indicators`): SMA, EMA, RSI (Wilder),
MACD, Bollinger Bands — hepsi sıfırdan pandas/numpy ile yazıldı (şeffaflık
için), plug-in mimarisiyle kayıtlı, config'ten açılıp kapatılabilir. Gerçek
referans veri üzerinde test edildi, sonuçlar sağlıklı.

```bash
python -m src.indicators.pipeline
```

**Adım 3 — Temel Strateji** (`src/strategies`): Önce MACD+Stokastik ile
başlanmıştı, ama bu kullanıcının rastgele attığı bir fikirdi — asıl istek
"araştır, kanıta dayalı bir strateji seç"ti. BTC'ye özel akademik/
kantitatif araştırma yapıldı (Grayscale, SSRN, QuantPedia): sonuç, BTC'de
**trend-takip stratejilerinin mean-reversion'dan belirgin şekilde daha
dayanıklı (out-of-sample'da bile)** olduğu yönünde. Bunun üzerine ana
strateji **Donchian Channel Breakout + uzun vadeli trend filtresi** olarak
seçildi (70 yıldır test edilmiş, az parametreli, klasik bir trend-takip
sistemi). MACD+Stokastik de plug-in mimarisi sayesinde kayıtlı kaldı,
config'ten karşılaştırma için seçilebilir.

```bash
python -m src.strategies.pipeline
```

Gerçek referans veride (2020-2026, 58.728 mum) 1.512 AL + 2.337 SAT sinyali
üretti — **bu henüz backtest değil ve "işlem sayısı" da değil** (sinyal
katmanı pozisyon durumunu takip etmiyor, bilinçli bir tasarım kararı —
detay `src/strategies/README.md`'de). Hangi sinyallerin kârlı olduğu, gerçek
işlem sayısının ne olacağı adım 4'te (walk-forward backtest, fee+slipaj
dahil) ölçülecek.

Kullanıcıyla üzerinde anlaşıldığı gibi: **Smart Money Concept** (order
block/BOS-CHoCH/FVG) katmanı bu temel doğrulandıktan sonra üçüncü bir
confluence bileşeni olarak eklenecek.

**Adım 4 — Backtest Motoru** (`src/backtest`): Sinyalleri gerçek işlemlere
çeviren, fee+slipaj uygulayan, look-ahead bias'tan kaçınan (bar X+1'in
açılışında işlem), yıllık ve piyasa rejimi (BOĞA/AYI/YATAY, veriye dayalı
sınıflandırma) bazlı dökümü üreten motor.

```bash
python -m src.backtest.pipeline
```

**Önemli — geliştirme sırasında bir hata bulundu ve düzeltildi:**
Donchian stratejisinin parametreleri ("Turtle System 2" 55/20 gün + 200
günlük trend filtresi) ilk halde saate çevrilmeden kullanılmıştı. Bu haliyle
backtest **-2.25% getiri** (Buy&Hold: +977%) verdi - neredeyse rastgele bir
sistem. Hata (birim ölçeklendirme) düzeltildikten sonra (×24 ile saate
çevrildi): **+644.69% getiri, Sharpe 1.04, max drawdown -33.49%, 16 işlem,
%62.5 kazanma oranı**. Buy&Hold'u mutlak getiride hâlâ geçemedi ama çok daha
düşük risk/drawdown ile. **İşlem sayısı (16) istatistiksel olarak küçük** -
bu sonuçlara yüksek güvenle "çalışıyor" denemez. Tüm dürüst detaylar, yıllık
ve rejim bazlı döküm `src/backtest/README.md`'de.

Sıradaki adımlar: risk yönetimi (5) → raporlama (6). Ayrıca kullanıcıyla
konuşulması gereken açık nokta: bu sonuçlar **referans veride** (OKX değil)
- gerçek OKX verisiyle doğrulama hâlâ bekliyor.

## Test

```bash
python -m pytest -v
```

## Overfitting üzerine not

Bu proje ilerledikçe her backtest sonucunda şunu soracağız: *bu performans
gerçek piyasada tekrarlanabilir mi, yoksa geçmiş veriye mi uydurulmuş?*
Walk-forward test, out-of-sample doğrulama ve farklı piyasa rejimlerinde
ayrı test bu yüzden zorunlu tutulacak (bkz. Adım 4 planı). İyimser
yorumlardan kaçınıp şüpheli bulguları açıkça belirteceğiz.
