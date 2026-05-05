"""Testes para src/pr_analyzer/llm/classifiers.py — TASK-09."""

from unittest.mock import MagicMock

import pytest

from pr_analyzer.llm.classifiers import (
    CONTRIBUTION_NATURES,
    DESCRIPTION_CLARITY_LEVELS,
    PROJECT_TYPES,
    classify_contribution_nature,
    classify_description_clarity,
    classify_project_type,
)


@pytest.fixture()  # type: ignore[misc]
def mock_client() -> MagicMock:
    return MagicMock()


# ── frozensets ────────────────────────────────────────────────────────────────


def test_project_types_é_frozenset() -> None:
    assert isinstance(PROJECT_TYPES, frozenset)


def test_contribution_natures_é_frozenset() -> None:
    assert isinstance(CONTRIBUTION_NATURES, frozenset)


def test_description_clarity_levels_é_frozenset() -> None:
    assert isinstance(DESCRIPTION_CLARITY_LEVELS, frozenset)


def test_project_types_não_está_vazio() -> None:
    assert len(PROJECT_TYPES) > 0


def test_contribution_natures_não_está_vazio() -> None:
    assert len(CONTRIBUTION_NATURES) > 0


def test_description_clarity_levels_não_está_vazio() -> None:
    assert len(DESCRIPTION_CLARITY_LEVELS) > 0


# ── classify_project_type ─────────────────────────────────────────────────────


def test_classify_project_type_retorna_valor_válido(mock_client: MagicMock) -> None:
    result = classify_project_type("my-repo", ["fix bug", "add feature"], mock_client)
    assert result in PROJECT_TYPES


def test_classify_project_type_retorna_string(mock_client: MagicMock) -> None:
    result = classify_project_type("repo", ["title"], mock_client)
    assert isinstance(result, str)


def test_classify_project_type_aceita_lista_vazia(mock_client: MagicMock) -> None:
    result = classify_project_type("repo", [], mock_client)
    assert result in PROJECT_TYPES


# ── classify_contribution_nature ──────────────────────────────────────────────


def test_classify_contribution_nature_retorna_valor_válido(
    mock_client: MagicMock,
) -> None:
    result = classify_contribution_nature(
        "Fix memory leak", "Detailed description here.", mock_client
    )
    assert result in CONTRIBUTION_NATURES


def test_classify_contribution_nature_retorna_string(mock_client: MagicMock) -> None:
    result = classify_contribution_nature("title", "body", mock_client)
    assert isinstance(result, str)


def test_classify_contribution_nature_aceita_body_vazio(mock_client: MagicMock) -> None:
    result = classify_contribution_nature("title", "", mock_client)
    assert result in CONTRIBUTION_NATURES


# ── classify_description_clarity ──────────────────────────────────────────────


def test_classify_description_clarity_retorna_valor_válido(
    mock_client: MagicMock,
) -> None:
    result = classify_description_clarity("Some PR body text with detail.", mock_client)
    assert result in DESCRIPTION_CLARITY_LEVELS


def test_classify_description_clarity_retorna_string(mock_client: MagicMock) -> None:
    result = classify_description_clarity("body", mock_client)
    assert isinstance(result, str)


def test_classify_description_clarity_aceita_body_vazio(mock_client: MagicMock) -> None:
    result = classify_description_clarity("", mock_client)
    assert result in DESCRIPTION_CLARITY_LEVELS
