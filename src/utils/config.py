"""Proje genelinde kullanılan YAML config dosyasını okuyan yardımcı modül."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "settings.yaml"


def load_config(path=None):
    """`config/settings.yaml` dosyasını (veya verilen yolu) okuyup dict olarak döner."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config or {}
