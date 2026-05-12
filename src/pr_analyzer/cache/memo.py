import hashlib
import json
from collections import OrderedDict
from collections.abc import Callable
from functools import wraps
from pathlib import Path

_SEP = "\x00"


def make_cache_key(*args: str) -> str:
    raw = _SEP.join(args)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def cached_classify(
    classifier_fn: Callable[..., str],
    cache_size: int = 1024,
    cache_path: Path | None = None,
) -> Callable[..., str]:
    store: OrderedDict[str, str] = OrderedDict()

    if cache_path and cache_path.exists():
        store.update(json.loads(cache_path.read_text(encoding="utf-8")))

    @wraps(classifier_fn)
    def wrapper(*args: str) -> str:
        key = make_cache_key(*args)
        if key in store:
            store.move_to_end(key)
            return store[key]

        result = classifier_fn(*args)
        store[key] = result

        if len(store) > cache_size:
            store.popitem(last=False)

        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(dict(store), indent=2), encoding="utf-8")

        return result

    return wrapper
