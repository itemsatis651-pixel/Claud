"""Strateji katmanını çalıştıran orkestrasyon modülü.

Config'teki `strategy.active` alanında seçilen stratejiyi, indikatörlerle
zenginleştirilmiş DataFrame üzerine uygular ve sinyal sütunlarını
(`signal`, `signal_score`, `signal_reasons`) ekler.

Tek başına çalıştırma: `python -m src.strategies.pipeline`
"""

import logging

import src.strategies.donchian_breakout  # noqa: F401 - import side effect: stratejiyi kaydeder
import src.strategies.macd_stochastic  # noqa: F401 - import side effect: stratejiyi kaydeder
from src.indicators.pipeline import run as run_indicators
from src.strategies.registry import get_strategy
from src.utils.config import load_config

logger = logging.getLogger(__name__)


def apply_strategy(df, strategy_config):
    """Config'teki aktif stratejiyi df'e uygular, sinyal sütunlarını ekler."""
    strategy_config = dict(strategy_config or {})
    name = strategy_config.get("active")
    if not name:
        raise ValueError("config.strategy.active belirtilmeli (örn. 'macd_stochastic')")

    params = dict(strategy_config.get(name, {}) or {})
    func = get_strategy(name)
    return func(df, **params)


def run(config=None, input_csv=None):
    config = config or load_config()
    df, source = run_indicators(config=config, input_csv=input_csv)
    result = apply_strategy(df, config.get("strategy"))
    return result, source


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    df, source = run()

    print(f"Veri kaynağı: {source}")
    cols = ["timestamp", "close", "signal", "signal_score", "signal_reasons"]
    print(df[cols].tail(15).to_string())

    print("\nSinyal dağılımı:")
    print(df["signal"].value_counts().to_string())


if __name__ == "__main__":
    main()
