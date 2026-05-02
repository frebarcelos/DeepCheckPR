import hashlib

_SEP = "\x00"


def make_cache_key(*args: str) -> str:
    raw = _SEP.join(args)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
