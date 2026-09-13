# BTC Al/Sat Sinyal ve Backtest Sistemi

BTC için kural tabanlı al/sat sinyalleri üreten, gerçekçi (fee + slipaj
dahil) walk-forward backtest yapabilen, kişisel araştırma/analiz amaçlı
modüler bir sistem.

**Bu bir yatırım tavsiyesi aracı değildir.** Backtest sonuçları geçmiş
performansı gösterir; gelecekte tekrarlanacağının garantisi yoktur. Her
adımda overfitting riskine karşı dürüst bir değerlendirme yapılacak.

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
  indicators/         # (sonraki adım) Teknik indikatörler
  strategies/         # (sonraki adım) Kural tabanlı stratejiler
  backtest/           # (sonraki adım) Walk-forward backtest motoru
  risk/               # (sonraki adım) Pozisyon boyutlandırma, stop-loss, kayıp limitleri
  reporting/          # (sonraki adım) Equity curve, drawdown, işlem istatistikleri
tests/                # Her modül için birim testler
```

Her alt modülün kendi `README.md`'si var — aylar sonra geri dönüldüğünde
"bu modül ne yapıyordu" sorusuna hızlı cevap vermesi için.

## Mevcut durum (Adım 1/6: Veri Katmanı)

`src/data` modülü tamamlandı: OKX'ten (kullanıcının işlem yaptığı borsa)
1 saatlik BTC/USDT mumlarını çeker, temizler (kopya/eksik/mantıksız mum
tespiti), zaman boşluklarını raporlar, ve incremental cache ile tekrar
çalıştırıldığında sadece eksik veriyi çeker.

```bash
python -m src.data.pipeline
```

**Önemli:** Bu geliştirme ortamının ağ politikası OKX API'sine erişimi
engelliyor, bu yüzden canlı veri çekme burada test edilemedi (mantık 13
birim testle mock veriyle doğrulandı — detaylar `src/data/README.md`'de).
Komutu kendi makinenizde çalıştırıp gerçek veri çekildiğini teyit edin.

Sıradaki adımlar: teknik indikatörler (2) → basit kural tabanlı strateji (3)
→ walk-forward backtest (4) → risk yönetimi (5) → raporlama (6).

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
