"""Backtest katmanını uçtan uca çalıştıran orkestrasyon modülü.

Akış: veri -> indikatörler -> strateji -> backtest motoru -> metrikler ->
rejim/yıl bazlı dökümü -> dürüst özet rapor.

Tek başına çalıştırma: `python -m src.backtest.pipeline`

## Önemli tasarım kararı: TEK sürekli simülasyon

Backtest **bir kez, kesintisiz** çalıştırılır (tüm tarih aralığı boyunca tek
bir equity curve ve işlem listesi). "Yıllık" ve "rejim bazlı" raporlar bu
TEK simülasyonun üzerine dilimleme/gruplama yaparak üretilir - veriyi
parçalara bölüp her parçayı ayrı ayrı simüle ETMEZ. Bunun sebebi: bir işlem
bir yılın/rejimin ortasında açılıp başka birinde kapanabilir; simülasyonu
parçalara bölmek pozisyon sürekliliğini bozar ve yapay/yanıltıcı sonuçlar
üretir. Bu yüzden:
- **Yıllık dökümü:** equity curve'ün o takvim yılındaki başlangıç/bitiş
  değerlerinden basit getiri (segment return) hesaplanır.
- **Rejim dökümü:** her TAMAMLANMIŞ işlem, GİRİŞ barındaki rejime göre
  gruplanır (işlem süresince rejim değişmiş olabilir - bu bir basitleştirme,
  aşağıda not edildi).
"""

import logging

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.metrics import compute_metrics, segment_return_pct
from src.backtest.regime import classify_regime
from src.strategies.pipeline import run as run_strategy
from src.utils.config import load_config

logger = logging.getLogger(__name__)


def run(config=None, input_csv=None):
    config = config or load_config()
    bt_cfg = config.get("backtest") or {}

    df, source = run_strategy(config=config, input_csv=input_csv)

    result = run_backtest(
        df,
        initial_capital=bt_cfg.get("initial_capital", 10000.0),
        fee_bps=bt_cfg.get("fee_bps", 10.0),
        slippage_bps=bt_cfg.get("slippage_bps", 5.0),
    )

    periods_per_year = bt_cfg.get("periods_per_year", 8766)
    overall_metrics = compute_metrics(
        result["equity"], result["trades"], periods_per_year, result["initial_capital"]
    )

    regime_cfg = bt_cfg.get("regime", {})
    regime = classify_regime(
        df,
        sma_period=regime_cfg.get("sma_period", 4800),
        slope_lookback=regime_cfg.get("slope_lookback", 720),
        bull_threshold=regime_cfg.get("bull_threshold", 0.05),
        bear_threshold=regime_cfg.get("bear_threshold", -0.05),
    )
    regime_by_time = pd.Series(regime.to_numpy(), index=pd.to_datetime(df["timestamp"]).to_numpy())

    yearly = _yearly_breakdown(result["equity"])
    regime_breakdown = _regime_trade_breakdown(result["trades"], regime_by_time)

    oos_start = bt_cfg.get("out_of_sample_start")
    in_sample_return = segment_return_pct(result["equity"], end=pd.Timestamp(oos_start) if oos_start else None)
    out_of_sample_return = segment_return_pct(result["equity"], start=pd.Timestamp(oos_start) if oos_start else None)

    return {
        "source": source,
        "df": df,
        "backtest": result,
        "overall_metrics": overall_metrics,
        "yearly": yearly,
        "regime_breakdown": regime_breakdown,
        "in_sample_return_pct": in_sample_return,
        "out_of_sample_return_pct": out_of_sample_return,
        "oos_start": oos_start,
        "periods_per_year": periods_per_year,
    }


def _yearly_breakdown(equity):
    years = sorted(equity.index.year.unique())
    rows = []
    for year in years:
        start = pd.Timestamp(f"{year}-01-01", tz=equity.index.tz)
        end = pd.Timestamp(f"{year + 1}-01-01", tz=equity.index.tz)
        ret = segment_return_pct(equity, start=start, end=end)
        rows.append({"year": year, "return_pct": ret})
    return pd.DataFrame(rows)


def _regime_trade_breakdown(trades, regime_by_time):
    if len(trades) == 0:
        return pd.DataFrame(columns=["regime", "num_trades", "win_rate_pct", "avg_return_pct", "total_pnl"])

    entry_regimes = []
    for entry_time in trades["entry_time"]:
        idx = regime_by_time.index.searchsorted(entry_time, side="right") - 1
        entry_regimes.append(regime_by_time.iloc[idx] if idx >= 0 else None)

    trades = trades.copy()
    trades["entry_regime"] = entry_regimes

    rows = []
    for regime_name, group in trades.groupby("entry_regime", dropna=True):
        wins = group[group["pnl"] > 0]
        rows.append(
            {
                "regime": regime_name,
                "num_trades": len(group),
                "win_rate_pct": len(wins) / len(group) * 100,
                "avg_return_pct": group["return_pct"].mean() * 100,
                "total_pnl": group["pnl"].sum(),
            }
        )
    return pd.DataFrame(rows)


def _print_report(result_bundle):
    m = result_bundle["overall_metrics"]
    bt = result_bundle["backtest"]

    print(f"Veri kaynağı: {result_bundle['source']}")
    print(f"Toplam bar: {len(result_bundle['df'])}, kapsanan yıl: {m['years_covered']:.2f}")
    print()
    print("=== GENEL SONUÇLAR (tek, kesintisiz simülasyon) ===")
    print(f"Başlangıç sermaye: {m['initial_capital']:,.2f}")
    print(f"Son sermaye: {m['final_equity']:,.2f}")
    print(f"Toplam getiri: {m['total_return_pct']:.2f}%")
    print(f"CAGR: {m['cagr_pct']:.2f}%")
    print(f"Sharpe (risksiz oran=0 varsayımıyla): {m['sharpe']:.2f}")
    print(f"Sortino: {m['sortino']:.2f}")
    print(f"Maksimum drawdown: {m['max_drawdown_pct']:.2f}%")
    print()
    print(f"İşlem sayısı: {m['num_trades']}")
    print(f"Kazanma oranı: {m['win_rate_pct']:.1f}%")
    print(f"Ortalama kazanç: {m['avg_win_pct']:.2f}% | Ortalama kayıp: {m['avg_loss_pct']:.2f}%")
    print(f"Profit factor: {m['profit_factor']:.2f}")
    print(f"Ortalama pozisyon süresi: {m['avg_bars_held']:.1f} bar (~{m['avg_bars_held']:.1f} saat)")
    print(f"Dönem sonunda açık pozisyon var mı: {bt['open_position_at_end']}")
    print()

    print("=== YILLIK DÖKÜMÜ (aynı sürekli simülasyonun yıl bazlı dilimi) ===")
    print(result_bundle["yearly"].to_string(index=False))
    print()

    print("=== REJİM BAZLI DÖKÜMÜ (işlemler GİRİŞ barındaki rejime göre gruplandı) ===")
    print(result_bundle["regime_breakdown"].to_string(index=False))
    print()

    oos_start = result_bundle["oos_start"]
    print(f"=== IN-SAMPLE / OUT-OF-SAMPLE (kesim tarihi: {oos_start}) ===")
    print(f"In-sample (öncesi) getiri: {result_bundle['in_sample_return_pct']:.2f}%")
    print(f"Out-of-sample (sonrası) getiri: {result_bundle['out_of_sample_return_pct']:.2f}%")
    print(
        "NOT: Bu strateji hiçbir parametre bu veri setine göre OPTİMİZE "
        "EDİLMEDİ (literatürden sabit alındı). Bu yüzden in/out-of-sample "
        "ayrımının amacı 'overfitting'i önlemek değil (zaten fit etmedik), "
        "sadece stratejinin zaman içinde TUTARLI davranıp davranmadığını "
        "görmek."
    )


def main():
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    result_bundle = run()
    _print_report(result_bundle)


if __name__ == "__main__":
    main()
