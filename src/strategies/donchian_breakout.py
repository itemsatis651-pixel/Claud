"""Donchian Channel Breakout + uzun vadeli trend filtresi.

## Neden bu strateji seçildi (araştırmaya dayalı)

Kullanıcı isteği üzerine ("iyice araştır ve seç") BTC'ye özel akademik/
kantitatif araştırma yapıldı. Birden fazla bağımsız kaynak aynı sonuca
işaret ediyor: **BTC güçlü ve kalıcı trendler sergiliyor, trend-takip/
momentum stratejileri mean-reversion'dan belirgin şekilde daha iyi ve daha
dayanıklı (out-of-sample'da bile) çalışıyor.**

Kaynaklar:
- Grayscale Research, "The Trend is Your Friend: Managing Bitcoin's
  Volatility with Momentum Signals"
- Rohrbach, Suremann, Osterrieder (SSRN), "Momentum and Trend Following
  Trading Strategies for Currencies and Bitcoin"
- QuantPedia, "Revisiting Trend-following and Mean-reversion Strategies in
  Bitcoin" (Kasım 2015 - Ağustos 2024 out-of-sample test): "MAX" (breakout
  tarzı trend) stratejisi sağlam kalırken "MIN" (mean-reversion) stratejisi
  out-of-sample'da zayıfladı - trend-takip belirgin şekilde daha dayanıklı
  bulundu.
- Çeşitli bağımsız backtest'ler (Coinquant, TrendSpider, TheTradingMuse):
  Donchian Channel Breakout "70 yıldır emtia/döviz/hisse senedi
  piyasalarında test edilmiş en basit ve en dayanıklı trend-takip
  sistemlerinden biri" olarak tanımlanıyor; BTC'nin kalıcı trend + yüksek
  oynaklık karakteri bu sistem için "ideal ortam" olarak değerlendiriliyor.
  Aynı zamanda ham (filtresiz) haliyle kısa zaman dilimlerinde (örn. 30dk)
  yatay/choppy piyasalarda zayıf performans gösterdiği ve bir trend
  filtresiyle (örn. uzun vadeli hareketli ortalama) birleştirildiğinde
  belirgin iyileştiği de aynı kaynaklarda dürüstçe raporlanıyor.

## Strateji mantığı

- **Giriş tetikleyicisi (AL):** Kapanış fiyatı, `entry_period` barlık Donchian
  üst bandını (BİR ÖNCEKİ bar'a göre - bkz. aşağıdaki look-ahead notu) yukarı
  kırarsa = "yeni N-bar zirvesi" = trend başlangıcı sinyali.
- **Çıkış tetikleyicisi (SAT):** Kapanış fiyatı, `exit_period` barlık
  (genellikle giriş periyodundan daha kısa) Donchian alt bandını aşağı
  kırarsa = "yeni M-bar dibi" = trend sonu/tersine dönüş sinyali. Çıkış
  girişten daha "gevşek" tutulur (daha kısa periyot) - bu, trend-takip
  sistemlerinde standart bir risk yönetimi prensibidir: kayıpları hızlı kes.
- **Trend filtresi:** AL sinyali sadece fiyat uzun vadeli hareketli ortalamanın
  (`trend_filter_period`, varsayılan SMA-200) ÜZERİNDEYKEN geçerli sayılır -
  araştırmadaki "yalnızca orta hat üzerindeyken long al" önerisini uygular,
  amaç düşüş trendindeki yanlış breakout'ları (whipsaw) azaltmak.

## Parametreler hakkında dürüstlük notu (ve düzeltilen bir hata)

`entry_period`/`exit_period`/`trend_filter_period` klasik "Turtle Trading
System 2" (55/20 gün) ve yaygın "200 günlük SMA" trend filtresinden
esinlenildi - **ama bunlar GÜNLÜK bar sayılarıdır**. İlk implementasyonda bu
sayılar (55, 20, 200) birebir SAATLİK bar sayısı olarak kullanılmıştı - bu
bir birim ölçeklendirme hatasıydı (55 saat ≈ 2.3 gün, oysa literatürdeki
sistem 55 GÜNLÜK bir pencereyi kastediyor). Bu haliyle adım 4'teki ilk
backtest'te gerçek veride **-2.25% toplam getiri** (Buy&Hold: +977%) çıktı -
whipsaw'a çok açık, neredeyse rastgele bir sistem gibi davrandı (profit
factor ≈ 1.00).

Hata fark edilip saatlik karşılıklarıyla düzeltildi: `entry_period=1320`
(55 gün × 24 saat), `exit_period=480` (20 gün × 24 saat),
`trend_filter_period=4800` (200 gün × 24 saat - zaten rejim
sınıflandırmasında kullanılan pencereyle aynı). **Bu bir "backtest'e göre
optimize etme" değil, bir birim dönüşüm düzeltmesidir** - literatürdeki
sistemi doğru şekilde saatlik barlara uyarlamak. Düzeltilmiş sonuç adım
4'ün raporunda (`src/backtest/README.md`) detaylandırıldı - çok daha makul
(+644.7% getiri, Sharpe 1.04, %62.5 kazanma oranı) ama sadece **16 işlem**
üzerine kurulu - istatistiksel örneklem küçük, bu da ayrıca not edildi.
Bu parametreler hâlâ bu veri setine optimize EDİLMEDİ, sadece doğru
ölçeklendirildi.

## Bilinen zayıflık (araştırmadan, dürüstçe)

Breakout sistemleri yatay/choppy piyasalarda çok sayıda yanlış sinyal
(whipsaw) üretir ve tipik kazanma oranı düşüktür (~%30-45) - kazanan
işlemlerin büyüklüğü kaybedenlerin sayısını telafi eder. Bu yüzden walk-
forward testte MUTLAKA rejim bazlı (boğa/ayı/yatay) ayrı sonuç
raporlayacağız - toplam getiri tek başına yanıltıcı olabilir.
"""

import numpy as np

from src.strategies.registry import register_strategy


@register_strategy("donchian_breakout")
def donchian_breakout_strategy(df, entry_period=1320, exit_period=480, trend_filter_period=4800, price_col="close"):
    entry_upper_col = f"donchian_{entry_period}_upper"
    exit_lower_col = f"donchian_{exit_period}_lower"
    trend_col = f"sma_{trend_filter_period}"

    for col in (entry_upper_col, exit_lower_col, trend_col):
        if col not in df.columns:
            raise KeyError(
                f"Strateji için gereken indikatör sütunu eksik: '{col}'. "
                "Önce indikatör katmanını (src.indicators.pipeline) çalıştırın "
                "ve entry_period/exit_period/trend_filter_period'ın indicators "
                "config'iyle (donchian.periods, sma.windows) eşleştiğinden emin olun."
            )

    df = df.copy()

    # Look-ahead bias'tan kaçınma: bugünün Donchian kanalı bugünün kendi
    # high/low'unu da içerir, o yüzden "bugünün kapanışı bugünün üst bandını
    # kırdı mı" sorusu anlamsızdır (üst bant zaten bugünün high'ını içerir).
    # Doğru breakout tanımı: kapanış, BİR ÖNCEKİ barda biten kanalın dışına
    # taşmış mı?
    prev_entry_upper = df[entry_upper_col].shift(1)
    prev_exit_lower = df[exit_lower_col].shift(1)

    breakout_up = df[price_col] > prev_entry_upper
    breakout_down = df[price_col] < prev_exit_lower
    trend_up = df[price_col] > df[trend_col]

    buy = breakout_up & trend_up
    sell = breakout_down

    df["signal"] = np.where(buy, "AL", np.where(sell, "SAT", "BEKLE"))

    trend_score = np.where(trend_up, 1, -1)
    breakout_score = np.where(breakout_up, 1, np.where(breakout_down, -1, 0))
    df["signal_score"] = trend_score + breakout_score  # kabaca -2..+2

    df["signal_reasons"] = _build_reasons(
        breakout_up.to_numpy(),
        breakout_down.to_numpy(),
        trend_up.to_numpy(),
        entry_period,
        exit_period,
        trend_filter_period,
    )

    return df


def _build_reasons(breakout_up, breakout_down, trend_up, entry_period, exit_period, trend_filter_period):
    reasons = []
    for i in range(len(breakout_up)):
        parts = []
        if breakout_up[i]:
            parts.append(f"Fiyat {entry_period} barlık Donchian üst bandını yukarı kırdı (yeni {entry_period}-bar zirvesi)")
        if breakout_down[i]:
            parts.append(f"Fiyat {exit_period} barlık Donchian alt bandını aşağı kırdı (yeni {exit_period}-bar dibi)")
        parts.append(
            f"Fiyat {trend_filter_period}-periyotluk SMA "
            + ("üzerinde (uzun vadeli trend yukarı)" if trend_up[i] else "altında (uzun vadeli trend aşağı)")
        )
        reasons.append("; ".join(parts) if parts else "Confluence yok")
    return reasons
