# TradingView / Pine Script Katmanı

BTC için al/sat sinyali üreten strateji artık **TradingView (Pine Script v6)**
üzerinde geliştiriliyor. Sebep: Python tarafında veri erişimi (borsa API'leri
bu geliştirme ortamından erişilemiyordu) sürekli sürtünme yaratıyordu;
TradingView kendi canlı OKX veri akışını sağlıyor ve Smart Money Concept
(order block, BOS/CHoCH, FVG) gibi doğası gereği görsel kavramları grafik
üzerinde doğrudan doğrulamak mümkün. Python tarafı (`src/`, `config/`,
`tests/`) SİLİNMEDİ — referans/yedek olarak repo'da duruyor.

## Dosyalar

- **`btc_smc_scalp_strategy.pine`** — Ana strateji script'i. Tek dosya,
  bölümlere ayrılmış (piyasa yapısı / order block / FVG / trend filtresi /
  giriş mantığı / risk yönetimi / alarm).

## Strateji mantığı

1. **Piyasa Yapısı:** Swing high/low tespiti (`ta.pivothigh`/`ta.pivotlow`),
   bunlardan Break of Structure (BOS - trend devamı) ve Change of Character
   (CHoCH - trend dönüşü) sinyalleri.
2. **Order Block:** BOS/CHoCH'a yol açan hareketten önceki son ters renkli
   mum, bir "kutu" olarak işaretlenir. Fiyat bu bölgeye geri dönüp kapanışla
   içinden geçmezse bölge geçerliliğini korur (mitigasyon = geçersizleşme).
3. **Fair Value Gap (FVG):** 3 mumluk fiyat boşluğu, ek bir giriş bölgesi
   olarak kullanılabilir (aç/kapa: `useFVG`).
4. **Trend Filtresi:** Uzun vadeli SMA - sadece bu yönde giriş alınır (aç/kapa:
   `useTrendFilter`).
5. **Giriş:** Yapı yönü (BOS/CHoCH) + trend filtresi + fiyatın OB/FVG
   bölgesine dokunup tepki vermesi (confluence) aynı anda sağlanınca.
6. **Risk Yönetimi:** Stop-loss, order block/FVG'nin diğer ucuna konur;
   pozisyon büyüklüğü `strategy.equity * risk% / stop mesafesi` formülüyle
   otomatik hesaplanır (yaklaşık sabit %risk/işlem - başta üzerinde
   anlaştığımız muhafazakar %1-2 risk yaklaşımını burada native olarak
   uyguluyoruz). Take-profit, R-katlı (`rewardRiskRatio`, varsayılan 2:1).

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

- **Bu script TradingView'de derlenerek TEST EDİLMEDİ** — ben (Claude) bu
  ortamda Pine Script çalıştıramıyorum/derleyemiyorum. Kod dikkatle, Pine v6
  sözdizimi kurallarına göre yazıldı ama derleme hatası veya beklenmedik
  davranış çıkarsa bana bildirin, düzeltip tekrar vereyim. **Bu, Python
  tarafındaki gibi "64 test geçti" güvencesine sahip değil** — yeni bir
  doğrulama döngüsüne giriyoruz.
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
