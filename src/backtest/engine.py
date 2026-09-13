"""Sinyal serisini (AL/SAT/BEKLE) gerçekçi bir işlem simülasyonuna çeviren motor.

## Gerçekçilik / look-ahead bias önlemleri

- **Bir bar sonra çalıştırma:** Strateji katmanı sinyali bar X'in
  KAPANIŞ fiyatına bakarak üretir. Gerçek hayatta bu bilgiyle en erken işlem
  yapabileceğiniz an bar X+1'in AÇILIŞIDIR - bar X henüz kapanmadan trade
  yapamazsınız. Bu motor bütün girişleri/çıkışları **bar X+1'in open
  fiyatından** gerçekleştirir. Bunu yapmayıp "aynı barın kapanışından işlem
  yap" varsayımı, backtest'lerde en yaygın ve en tehlikeli hatalardan
  biridir (gerçekte imkansız bir zamanlama avantajı verir, sonuçları
  olduğundan iyi gösterir).
- **Tek pozisyon, uzun-only:** Zaten pozisyondayken gelen AL sinyalleri ve
  zaten pozisyon dışındayken gelen SAT sinyalleri yok sayılır (no-op) -
  gerçek bir trader'ın davranışını simüle eder. Kısa (short) pozisyon
  desteklenmiyor (OKX spot hesabı varsayımıyla tutarlı).
- **Tam pozisyon büyüklüğü:** Her AL'de mevcut tüm sermaye kullanılır, her
  SAT'ta tamamen kapatılır. Kısmi pozisyon boyutlandırma / stop-loss ADIM 5
  (risk yönetimi) katmanında eklenecek - bu motor SADECE sinyal kalitesini
  ölçmek için "tam pozisyon" varsayımıyla çalışır.
- **Fee + slipaj:** Her giriş/çıkışta `fee_bps` (borsa işlem ücreti, baz
  puan) ve `slippage_bps` (fiyatın beklenenden ne kadar kötü gerçekleştiği,
  baz puan) uygulanır. Alışta fiyat yukarı, satışta aşağı kaydırılarak
  simüle edilir.
- **Nakit faizsiz:** Pozisyon dışındayken nakit getirisiz varsayılır (gerçekte
  kısa vadeli faiz/staking getirisi olabilir) - muhafazakar bir basitleştirme.
"""

import numpy as np
import pandas as pd


def run_backtest(df, initial_capital=10000.0, fee_bps=10.0, slippage_bps=5.0, price_col="close", open_col="open"):
    """Sinyal içeren df'i simüle eder.

    `df` şunları içermeli: `timestamp`, `open`, `close`, `signal` (AL/SAT/BEKLE).

    Döner: {"equity": pd.Series (timestamp indeksli), "position": pd.Series
    (0/1), "trades": pd.DataFrame, "open_position_at_end": bool}
    """
    df = df.reset_index(drop=True)
    n = len(df)

    fee_rate = fee_bps / 10_000
    slippage_rate = slippage_bps / 10_000

    signals = df["signal"].to_numpy()
    opens = df[open_col].to_numpy(dtype="float64")
    closes = df[price_col].to_numpy(dtype="float64")
    timestamps = df["timestamp"].to_numpy()

    position = 0
    cash = float(initial_capital)
    units = 0.0
    entry_price = None
    entry_time = None
    entry_index = None
    entry_capital = None

    equity = np.empty(n, dtype="float64")
    position_state = np.zeros(n, dtype="int8")
    trades = []

    for i in range(n):
        if i > 0:
            signal_prev = signals[i - 1]
            exec_price = opens[i]

            if position == 0 and signal_prev == "AL":
                entry_capital = cash
                fill_price = exec_price * (1 + slippage_rate)
                fee = entry_capital * fee_rate
                units = (entry_capital - fee) / fill_price
                cash = 0.0
                position = 1
                entry_price = fill_price
                entry_time = timestamps[i]
                entry_index = i

            elif position == 1 and signal_prev == "SAT":
                fill_price = exec_price * (1 - slippage_rate)
                proceeds = units * fill_price
                fee = proceeds * fee_rate
                cash = proceeds - fee
                trades.append(
                    {
                        "entry_time": entry_time,
                        "entry_price": entry_price,
                        "exit_time": timestamps[i],
                        "exit_price": fill_price,
                        "bars_held": i - entry_index,
                        "capital_at_entry": entry_capital,
                        "capital_at_exit": cash,
                        "pnl": cash - entry_capital,
                        "return_pct": (cash / entry_capital) - 1,
                    }
                )
                units = 0.0
                position = 0
                entry_price = None
                entry_time = None
                entry_index = None
                entry_capital = None

        equity[i] = cash + units * closes[i]
        position_state[i] = position

    open_position_at_end = position == 1

    equity_series = pd.Series(equity, index=pd.DatetimeIndex(timestamps), name="equity")
    position_series = pd.Series(position_state, index=pd.DatetimeIndex(timestamps), name="position")
    trades_df = pd.DataFrame(trades)

    return {
        "equity": equity_series,
        "position": position_series,
        "trades": trades_df,
        "open_position_at_end": open_position_at_end,
        "initial_capital": float(initial_capital),
    }
