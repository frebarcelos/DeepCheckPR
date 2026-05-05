import pytest

from pr_analyzer.pipeline.builder import build_pipeline, compose, pipe


def test_compose_is_callable() -> None:
    assert callable(compose)


def test_pipe_is_callable() -> None:
    assert callable(pipe)


def test_build_pipeline_is_callable() -> None:
    assert callable(build_pipeline)


def test_compose_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        compose(str, int)


def test_pipe_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        pipe("value", str)


def test_build_pipeline_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        build_pipeline(str, int)
