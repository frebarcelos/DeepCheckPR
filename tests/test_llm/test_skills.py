"""Testes para src/pr_analyzer/llm/skills.py — TDD."""

import json

import pytest

from pr_analyzer.llm.skills import (
    CLASSIFIER_SYSTEM_PROMPT,
    FEW_SHOT_CONTRIBUTION_NATURE,
    FEW_SHOT_DESCRIPTION_CLARITY,
    FEW_SHOT_PROJECT_TYPE,
)


def test_system_prompt_is_non_empty_str() -> None:
    assert isinstance(CLASSIFIER_SYSTEM_PROMPT, str)
    assert len(CLASSIFIER_SYSTEM_PROMPT) > 0


def test_system_prompt_contains_json_instruction() -> None:
    assert "JSON" in CLASSIFIER_SYSTEM_PROMPT


def test_few_shot_project_type_is_non_empty_tuple() -> None:
    assert isinstance(FEW_SHOT_PROJECT_TYPE, tuple)
    assert len(FEW_SHOT_PROJECT_TYPE) >= 1


def test_few_shot_nature_is_non_empty_tuple() -> None:
    assert isinstance(FEW_SHOT_CONTRIBUTION_NATURE, tuple)
    assert len(FEW_SHOT_CONTRIBUTION_NATURE) >= 1


def test_few_shot_clarity_is_non_empty_tuple() -> None:
    assert isinstance(FEW_SHOT_DESCRIPTION_CLARITY, tuple)
    assert len(FEW_SHOT_DESCRIPTION_CLARITY) >= 1


@pytest.mark.parametrize(
    "shots",
    [FEW_SHOT_PROJECT_TYPE, FEW_SHOT_CONTRIBUTION_NATURE, FEW_SHOT_DESCRIPTION_CLARITY],
)
def test_each_shot_is_a_str_pair(shots: tuple[tuple[str, str], ...]) -> None:
    for user_shot, assistant_shot in shots:
        assert isinstance(user_shot, str)
        assert len(user_shot) > 0
        assert isinstance(assistant_shot, str)
        assert len(assistant_shot) > 0


@pytest.mark.parametrize(
    "shots",
    [FEW_SHOT_PROJECT_TYPE, FEW_SHOT_CONTRIBUTION_NATURE, FEW_SHOT_DESCRIPTION_CLARITY],
)
def test_assistant_shots_are_valid_json(shots: tuple[tuple[str, str], ...]) -> None:
    for _, assistant_shot in shots:
        parsed = json.loads(assistant_shot)
        assert isinstance(parsed, dict)


def test_project_type_shots_use_tipo_projeto_key() -> None:
    for _, assistant_shot in FEW_SHOT_PROJECT_TYPE:
        assert "tipo_projeto" in json.loads(assistant_shot)


def test_nature_shots_use_natureza_key() -> None:
    for _, assistant_shot in FEW_SHOT_CONTRIBUTION_NATURE:
        assert "natureza" in json.loads(assistant_shot)


def test_clarity_shots_use_clareza_key() -> None:
    for _, assistant_shot in FEW_SHOT_DESCRIPTION_CLARITY:
        assert "clareza" in json.loads(assistant_shot)
