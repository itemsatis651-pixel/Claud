"""MACD + Stokastik confluence stratejisi.

Kural (bilinçli olarak basit tutuldu - "karmaşık ML modeline geçmeden önce
basit kural tabanlı strateji" hedefiyle):

- **Trend filtresi (MACD):** histogram > 0 ise yukarı momentum, < 0 ise aşağı
  momentum.
- **Zamanlama tetikleyicisi (Stokastik):** %K'nın %D'yi aşırı satım
  bölgesinden (%D < `oversold`) yukarı kesmesi = alım tetiği; aşırı alım
  bölgesinden (%D > `overbought`) aşağı kesmesi = satım tetiği.
- **Confluence:** Trend filtresi ve tetikleyici aynı yönde ise net AL/SAT
  sinyali üretilir; aksi halde BEKLE.

Smart Money Concept (order block / BOS-CHoCH / FVG) katmanı, temel bu iki
indikatörle çalışan strateji doğrulandıktan sonra ayrı bir confluence
bileşeni olarak eklenecek (kullanıcıyla üzerinde anlaşıldığı gibi).

ÖNEMLİ - overfitting notu: `oversold`/`overbought` eşikleri (20/80) ve MACD/
Stokastik parametreleri (12,26,9 / 14,3,3) piyasada yaygın kullanılan
standart varsayılanlardır, bu veri setine özel optimize edilmemiştir. Adım
4'teki walk-forward backtest'te bu haliyle test edilecek; sonuçlar kötüyse
parametre taraması yapmak yerine önce stratejinin temel mantığını
sorgulayacağız (parametre taraması = overfitting kapısı).
"""

import numpy as np

from src.strategies.registry import register_strategy


@register_strategy("macd_stochastic")
def macd_stochastic_strategy(df, macd_prefix="macd_12_26_9", stoch_prefix="stoch_14_3_3", oversold=20, overbought=80):
    hist_col = f"{macd_prefix}_hist"
    k_col = f"{stoch_prefix}_k"
    d_col = f"{stoch_prefix}_d"

    for col in (hist_col, k_col, d_col):
        if col not in df.columns:
            raise KeyError(
                f"Strateji için gereken indikatör sütunu eksik: '{col}'. "
                "Önce indikatör katmanını (src.indicators.pipeline) çalıştırın "
                "ve macd_prefix/stoch_prefix'in indicators config'iyle eşleştiğinden emin olun."
            )

    df = df.copy()

    macd_bullish = df[hist_col] > 0
    macd_bearish = df[hist_col] < 0

    k_prev = df[k_col].shift(1)
    d_prev = df[d_col].shift(1)
    bullish_cross = (k_prev <= d_prev) & (df[k_col] > df[d_col])
    bearish_cross = (k_prev >= d_prev) & (df[k_col] < df[d_col])

    stoch_bullish_trigger = bullish_cross & (d_prev < oversold)
    stoch_bearish_trigger = bearish_cross & (d_prev > overbought)

    buy = macd_bullish & stoch_bullish_trigger
    sell = macd_bearish & stoch_bearish_trigger

    df["signal"] = np.where(buy, "AL", np.where(sell, "SAT", "BEKLE"))

    macd_score = np.where(macd_bullish, 1, np.where(macd_bearish, -1, 0))
    stoch_score = np.where(stoch_bullish_trigger, 1, np.where(stoch_bearish_trigger, -1, 0))
    df["signal_score"] = macd_score + stoch_score  # -2..+2 aralığında

    df["signal_reasons"] = _build_reasons(
        macd_bullish.to_numpy(),
        macd_bearish.to_numpy(),
        stoch_bullish_trigger.to_numpy(),
        stoch_bearish_trigger.to_numpy(),
        oversold,
        overbought,
    )

    return df


def _build_reasons(macd_bullish, macd_bearish, stoch_bullish_trigger, stoch_bearish_trigger, oversold, overbought):
    reasons = []
    for i in range(len(macd_bullish)):
        parts = []
        if macd_bullish[i]:
            parts.append("MACD histogram pozitif (yukarı momentum)")
        elif macd_bearish[i]:
            parts.append("MACD histogram negatif (aşağı momentum)")

        if stoch_bullish_trigger[i]:
            parts.append(f"Stokastik %K, %D'yi aşırı satım bölgesinden (<{oversold}) yukarı kesti")
        if stoch_bearish_trigger[i]:
            parts.append(f"Stokastik %K, %D'yi aşırı alım bölgesinden (>{overbought}) aşağı kesti")

        reasons.append("; ".join(parts) if parts else "Confluence yok")
    return reasons
