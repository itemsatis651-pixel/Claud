# TradingView / Pine Script Katmanı

BTC için al/sat sinyali üreten strateji artık **TradingView (Pine Script v6)**
üzerinde geliştiriliyor. Sebep: Python tarafında veri erişimi (borsa API'leri
bu geliştirme ortamından erişilemiyordu) sürekli sürtünme yaratıyordu;
TradingView kendi canlı OKX veri akışını sağlıyor ve Smart Money Concept
(order block, BOS/CHoCH, FVG) gibi doğası gereği görsel kavramları grafik
üzerinde doğrudan doğrulamak mümkün. Python tarafı (`src/`, `config/`,
`tests/`) SİLİNMEDİ — referans/yedek olarak repo'da duruyor.

## Dosyalar

- **`btc_smc_scalp_strategy.pine`** — Ana strateji script'i (v2). Tek dosya,
  bölümlere ayrılmış (piyasa yapısı / order block / FVG / momentum / trend
  filtresi / giriş onayı / risk yönetimi / sinyal durumu / detay paneli).

## v2 değişiklikleri (v1'de kullanıcı geri bildirimiyle bulunan sorunlar)

v1 TradingView'de derlendi ve çalıştı, ama iki sorun bildirildi:

1. **Giriş zamanlaması kötüydü** ("düşeceği yerde al, çıkacağı yerde sat"):
   v1'de fiyat order block/FVG'ye sadece değip o bar biraz yeşil kapanınca
   hemen giriş veriliyordu - kısa vadeli/gürültülü grafiklerde bu, henüz
   gerçek bir tepki oluşmadan tam tepe/dip noktasında tetikleniyordu.
   **Düzeltme:** İki aşamalı onay - fiyat bölgeye dokunur (beklemede
   işaretlenir), sonra `confirmMaxBars` bar içinde bölgenin üst/alt
   sınırını GERÇEK bir kapanışla geri kazanırsa (reclaim) giriş onaylanır.
2. **"Sadece AL/SAT/BEKLE + en detaylı gerekçe" isteği unutulmuştu:** v1
   sadece BOS/CHoCH etiketleri ve kutular çiziyordu, net bir sinyal durumu
   yoktu. **Düzeltme:** Sürekli görünen bir panel (AL/SAT/BEKLE + trend/
   yapı/momentum durumu + Long/Short skoru X/5 + eksik koşullar + nihai
   karar gerekçesi) ve grafik üzerinde AL/SAT/ÇIKIŞ etiketleri eklendi.
   BOS/CHoCH/OB/FVG görselleri artık varsayılan KAPALI (isteğe bağlı).

Ayrıca momentum onayı (RSI + MACD) eklendi - en başta konuşulan "MACD +
Stokastik/momentum + SMC" fikrinin momentum ayağı.

## Strateji mantığı

1. **Piyasa Yapısı:** Swing high/low tespiti (`ta.pivothigh`/`ta.pivotlow`),
   bunlardan Break of Structure (BOS - trend devamı) ve Change of Character
   (CHoCH - trend dönüşü) sinyalleri.
2. **Order Block:** BOS/CHoCH'a yol açan hareketten önceki son ters renkli
   mum, bir "kutu" olarak işaretlenir. Fiyat bu bölgeye geri dönüp kapanışla
   içinden geçmezse bölge geçerliliğini korur (mitigasyon = geçersizleşme).
   `obMaxAge` bar boyunca hiç test edilmezse "bayat" kabul edilip pasifleşir.
3. **Fair Value Gap (FVG):** 3 mumluk fiyat boşluğu, ek bir giriş bölgesi
   olarak kullanılabilir (aç/kapa: `useFVG`).
4. **Trend Filtresi:** Uzun vadeli SMA - sadece bu yönde giriş alınır (aç/kapa:
   `useTrendFilter`).
5. **Momentum Onayı:** RSI + MACD histogram aynı yönde olmalı (aç/kapa:
   `useMomentumFilter`).
6. **Giriş onayı (iki aşamalı):** (a) fiyat OB/FVG bölgesine dokunur, (b)
   `confirmMaxBars` bar içinde bölgenin üst/alt sınırını gerçek bir
   kapanışla geri kazanırsa (reclaim) onaylanır. Sadece "değme" yeterli
   değildir - bu, v1'de bulunan erken/yanlış zamanlı giriş sorununu çözmek
   için eklendi.
7. **Giriş:** Yapı yönü + trend filtresi + momentum + reclaim onayı hepsi
   aynı anda sağlanınca (5 koşullu confluence).
8. **Risk Yönetimi:** Stop-loss, order block/FVG'nin diğer ucuna konur;
   pozisyon büyüklüğü `strategy.equity * risk% / stop mesafesi` formülüyle
   otomatik hesaplanır (yaklaşık sabit %risk/işlem - başta üzerinde
   anlaştığımız muhafazakar %1-2 risk yaklaşımını burada native olarak
   uyguluyoruz). Take-profit, R-katlı (`rewardRiskRatio`, varsayılan 2:1).
9. **Sinyal durumu ve detay paneli:** Grafiğin sağ üstünde sürekli görünen
   panel - anlık AL/SAT/BEKLE, trend/yapı durumu, Long/Short skoru (X/5),
   eksik koşullar, nihai kararın gerekçesi. Grafik üzerinde de AL/SAT/ÇIKIŞ
   etiketleri (aç/kapa: `showSignalLabels`).

## Kurulum / Test

1. TradingView'de bir grafik açın (örn. `OKX:BTCUSDT`).
2. Pine Editor'ü açın, `btc_smc_scalp_strategy.pine` içeriğini yapıştırın.
3. "Add to Chart" ile ekleyin, **Strategy Tester** sekmesinden performansı
   inceleyin (Net Profit, Max Drawdown, Profit Factor, işlem listesi).
4. Ayarlar panelinden (⚙️) zaman dilimine göre parametreleri (özellikle
   `Swing Length`, `Trend Filtresi SMA Periyodu`) ayarlayın - bunlar bar
   SAYISI cinsindendir, grafik periyodunuza göre anlamı değişir.
5. **Bar Replay** özelliğiyle sinyallerin/kutuların bar bar nasıl oluştuğunu
   görsel olarak doğrulayabilirsiniz.

## Dürüstlük / bilinen sınırlamalar

- **v1 TradingView'de derlendi ve çalıştı** (kullanıcı ekran görüntüsüyle
  doğruladı) — ama v2'deki değişiklikler (momentum, iki aşamalı onay,
  panel) benim tarafımdan derlenip test EDİLMEDİ. Kod dikkatle Pine v6
  sözdizimine göre yazıldı ama derleme hatası veya beklenmedik davranış
  çıkarsa bildirin, düzeltip tekrar vereyim. **Bu, Python tarafındaki gibi
  "64 test geçti" güvencesine sahip değil.**
- **İki aşamalı onay hâlâ mükemmel değildir:** whipsaw riskini azaltır ama
  sıfırlamaz - özellikle çok kısa zaman dilimlerinde (1-3dk gibi) hâlâ
  yanlış sinyal üretebilir. `confirmMaxBars`, `swingLen`, `trendLen`
  parametrelerini kendi grafiğinizde deneyerek ayarlayın.
- **Swing tespiti gecikmeli:** Bir tepe/dip, ancak `swingLen` bar sonra
  "onaylanır" — bu SMC'nin doğasında var, repaint değil ama gerçek zamanlı
  sinyal her zaman birkaç bar gecikmeli gelir.
- **Order Block/FVG tanımları tartışmalı:** SMC topluluğunda "tek doğru"
  tanım yok, burada yaygın kullanılan bir versiyon uygulandı.
- **Parametreler optimize edilmedi:** Swing/trend/risk parametreleri makul
  başlangıç değerleri - kendi Strategy Tester'ınızda test ederken çok
  parametre ayarlayıp "geçmişe uydurma" (overfitting) riskine dikkat edin.
- **Slipaj Pine'da tick cinsinden** (yüzde değil) - gerçek OKX slipajını
  birebir yansıtmayabilir.
- **Short işlemler varsayılan kapalı** (`allowShorts=false`) - OKX spot
  hesabı short desteklemez, sadece margin/futures kullanıyorsanız açın.

## Sıradaki adımlar (konuşulacak)

- Script'i TradingView'de derleyip ilk test sonuçlarını paylaşın.
- Farklı zaman dilimlerinde (5dk/15dk/1sa) Strategy Tester sonuçlarını
  karşılaştırın.
- Hata/iyileştirme geri bildirimlerine göre iterasyon.
