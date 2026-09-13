"""Plug-in tarzı indikatör kayıt mekanizması.

Yeni bir indikatör eklemek için: bir fonksiyon yaz, `@register_indicator("isim")`
ile işaretle, modülünü `pipeline.py`'de import et. Config'te `indicators.isim`
altına parametrelerini ekleyince otomatik olarak devreye girer.
"""

_REGISTRY = {}


def register_indicator(name):
    def decorator(func):
        if name in _REGISTRY:
            raise ValueError(f"İndikatör zaten kayıtlı: {name}")
        _REGISTRY[name] = func
        return func

    return decorator


def get_indicator(name):
    if name not in _REGISTRY:
        raise KeyError(
            f"Bilinmeyen indikatör: '{name}'. Kayıtlı olanlar: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[name]


def available_indicators():
    return sorted(_REGISTRY.keys())
