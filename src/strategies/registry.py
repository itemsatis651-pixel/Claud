"""Plug-in tarzı strateji kayıt mekanizması (indikatör registry'siyle aynı desen).

Yeni bir strateji eklemek için: bir fonksiyon yaz, `@register_strategy("isim")`
ile işaretle, modülünü `pipeline.py`'de import et. Config'te `strategy.active`
o ismi seçince otomatik devreye girer.
"""

_REGISTRY = {}


def register_strategy(name):
    def decorator(func):
        if name in _REGISTRY:
            raise ValueError(f"Strateji zaten kayıtlı: {name}")
        _REGISTRY[name] = func
        return func

    return decorator


def get_strategy(name):
    if name not in _REGISTRY:
        raise KeyError(
            f"Bilinmeyen strateji: '{name}'. Kayıtlı olanlar: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[name]


def available_strategies():
    return sorted(_REGISTRY.keys())
