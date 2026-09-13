"""Fiyat verisinden objektif, veriye dayalı piyasa rejimi (boğa/ayı/yatay)
sınıflandırması.

## Neden bu yöntem

Rejim tarihlerini elle seçmek ("2021 boğa, 2022 ayı" gibi) stratejinin lehine
çalışacak tarihleri bilinçli/bilinçsiz seçme riski taşır (bir tür veri
casusluğu). Bunun yerine rejim, SADECE fiyat verisinden, önceden belirlenmiş
sabit bir kuralla otomatik hesaplanır: uzun vadeli bir hareketli ortalamanın
(`sma_period`) belirli bir pencerede (`slope_lookback`) ne kadar eğimli
olduğuna bakılır.

- **BOĞA:** uzun vadeli SMA, `slope_lookback` bar önceki değerine göre
  `bull_threshold`'dan fazla yükselmiş.
- **AYI:** aynı ölçüyle `bear_threshold`'dan fazla düşmüş.
- **YATAY:** ikisi de değil.
- **NaN (sınıflandırılamaz):** verinin başındaki ısınma (warmup) dönemi -
  `sma_period + slope_lookback` kadar bar, rejim hesaplanamaz.

Varsayılan parametreler (`sma_period=4800` ~200 gün, `slope_lookback=720`
~30 gün, eşikler ±%5) literatürde BTC boğa/ayı ayrımı için yaygın kullanılan
"200 günlük ortalama" yaklaşımından esinlenildi. Bu SINIRLI ve TARTIŞMALI
bir tanımdır - rejim sınıflandırmasının "doğru" tek bir yöntemi yoktur, bu
sadece nesnel/tekrarlanabilir bir tanesidir. Sonuçlar bu tanıma duyarlı
olabilir.
"""

import numpy as np
import pandas as pd


def classify_regime(df, price_col="close", sma_period=4800, slope_lookback=720, bull_threshold=0.05, bear_threshold=-0.05):
    sma = df[price_col].rolling(window=sma_period, min_periods=sma_period).mean()
    slope = sma / sma.shift(slope_lookback) - 1

    invalid = sma.isna() | slope.isna()

    regime = np.select(
        [slope > bull_threshold, slope < bear_threshold],
        ["BOĞA", "AYI"],
        default="YATAY",
    )
    regime = pd.Series(regime, index=df.index, dtype="object")
    regime[invalid] = None
    return regime
