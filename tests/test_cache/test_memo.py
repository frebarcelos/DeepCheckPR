from pr_analyzer.cache.memo import make_cache_key


def test_make_cache_key_is_deterministic() -> None:
    assert make_cache_key("123", "llama3") == make_cache_key("123", "llama3")


def test_make_cache_key_different_inputs_differ() -> None:
    assert make_cache_key("123", "llama3") != make_cache_key("456", "llama3")


def test_make_cache_key_returns_string() -> None:
    assert isinstance(make_cache_key("1", "model"), str)


def test_make_cache_key_order_matters() -> None:
    assert make_cache_key("a", "b") != make_cache_key("b", "a")


def test_make_cache_key_no_separator_collision() -> None:
    assert make_cache_key("a:b", "c") != make_cache_key("a", "b:c")
