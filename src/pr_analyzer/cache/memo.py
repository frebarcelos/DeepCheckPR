import hashlib
import json
from collections import OrderedDict
from collections.abc import Callable
from functools import wraps
from pathlib import Path

from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.pipeline.builder import EnrichedPR

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


def _derive_cache_path(base: Path | None, tag: str) -> Path | None:
    if base is None:
        return None
    return base.with_name(f"{base.stem}_{tag}{base.suffix}")


def make_enriched_classifier(
    classify_type_fn: Callable[..., str],
    classify_nature_fn: Callable[..., str],
    classify_clarity_fn: Callable[..., str],
    cache_path: Path | None = None,
    cache_size: int = 1024,
) -> Callable[[PRRecord], EnrichedPR]:
    """Envolve três classificadores com cache e retorna uma função para enrich_pipeline."""
    cached_type = cached_classify(
        classify_type_fn,
        cache_size=cache_size,
        cache_path=_derive_cache_path(cache_path, "type"),
    )
    cached_nature = cached_classify(
        classify_nature_fn,
        cache_size=cache_size,
        cache_path=_derive_cache_path(cache_path, "nature"),
    )
    cached_clarity = cached_classify(
        classify_clarity_fn,
        cache_size=cache_size,
        cache_path=_derive_cache_path(cache_path, "clarity"),
    )

    def _classify(pr: PRRecord) -> EnrichedPR:
        return EnrichedPR(
            pr=pr,
            project_type=cached_type(pr.repo_name, pr.title),
            contribution_nature=cached_nature(pr.title, pr.body[:300]),
            description_clarity=cached_clarity(pr.body[:500]),
        )

    return _classify
