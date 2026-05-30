"""Testes para src/pr_analyzer/transforms/heuristics.py — LLM-04 (TDD)."""

import pytest

from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.transforms.heuristics import (
    heuristic_clarity,
    heuristic_classify,
    heuristic_complexity,
    heuristic_nature,
)
from pr_analyzer.transforms.reducers import EnrichedPR

# ── fixtures ──────────────────────────────────────────────────────────────────


def _pr(title: str = "", body: str = "", repo: str = "org/repo") -> PRRecord:
    return PRRecord(
        pr_id="1",
        repo_name=repo,
        title=title,
        body=body,
        state="open",
        language="Python",
        created_at="",
        merged_at="",
        additions=0,
        deletions=0,
        changed_files=1,
    )


# ── heuristic_nature ─────────────────────────────────────────────────────────


def test_heuristic_nature_bug_retorna_bug_fix() -> None:
    assert heuristic_nature("bug: crash on login") == "bug fix"


def test_heuristic_nature_crash_retorna_bug_fix() -> None:
    assert heuristic_nature("crash on null pointer in auth") == "bug fix"


def test_heuristic_nature_add_retorna_feature() -> None:
    assert heuristic_nature("add dark mode support") == "feature"


def test_heuristic_nature_implement_retorna_feature() -> None:
    assert heuristic_nature("implement OAuth2 flow") == "feature"


def test_heuristic_nature_fix_sem_doc_retorna_bug_fix() -> None:
    # "fix" sem palavra de documentação → bug fix
    assert heuristic_nature("fix crash on startup") == "bug fix"


def test_heuristic_nature_doc_retorna_documentacao() -> None:
    assert heuristic_nature("update README installation guide") == "documentação"


def test_heuristic_nature_typo_retorna_documentacao() -> None:
    assert heuristic_nature("fix typo in changelog") == "documentação"


def test_heuristic_nature_refactor_retorna_refatoracao() -> None:
    assert heuristic_nature("refactor auth module") == "refatoração"


def test_heuristic_nature_rename_retorna_refatoracao() -> None:
    assert heuristic_nature("rename UserService to AccountService") == "refatoração"


def test_heuristic_nature_ambiguo_retorna_none() -> None:
    assert heuristic_nature("update configuration") is None


def test_heuristic_nature_vazio_retorna_none() -> None:
    assert heuristic_nature("") is None


def test_heuristic_nature_case_insensitive() -> None:
    assert heuristic_nature("FIX crash in prod") == "bug fix"


def test_heuristic_nature_palavras_parciais_nao_disparam() -> None:
    # "prefix" contém "fix" como substring mas não como palavra isolada
    assert heuristic_nature("prefix changes") is None


def test_heuristic_nature_hotfix_retorna_bug_fix() -> None:
    assert heuristic_nature("hotfix: memory leak") == "bug fix"


# ── heuristic_clarity ────────────────────────────────────────────────────────


def test_heuristic_clarity_body_vazio_retorna_insuficiente() -> None:
    assert heuristic_clarity("") == "insuficiente"


def test_heuristic_clarity_body_so_espacos_retorna_insuficiente() -> None:
    assert heuristic_clarity("   \n\t  ") == "insuficiente"


def test_heuristic_clarity_body_com_conteudo_retorna_none() -> None:
    assert heuristic_clarity("This PR fixes a crash in the auth module") is None


def test_heuristic_clarity_body_curto_retorna_none() -> None:
    # corpo curto mas não vazio → não temos certeza sem LLM
    assert heuristic_clarity("minor fix") is None


# ── heuristic_classify ────────────────────────────────────────────────────────


def test_heuristic_classify_titulo_e_body_vazios_retorna_enriched() -> None:
    pr = _pr(title="", body="")
    result = heuristic_classify(pr)
    assert result is not None
    assert isinstance(result, EnrichedPR)
    assert result.contribution_nature == "outro"
    assert result.description_clarity == "insuficiente"
    assert result.project_type == "outro"


def test_heuristic_classify_body_vazio_natureza_clara_retorna_enriched() -> None:
    pr = _pr(title="fix crash on login", body="")
    result = heuristic_classify(pr)
    assert result is not None
    assert result.contribution_nature == "bug fix"
    assert result.description_clarity == "insuficiente"


def test_heuristic_classify_body_vazio_natureza_ambigua_retorna_none() -> None:
    pr = _pr(title="update configuration", body="")
    assert heuristic_classify(pr) is None


def test_heuristic_classify_body_com_conteudo_retorna_none() -> None:
    # corpo com conteúdo: clareza não determinável sem LLM
    pr = _pr(title="fix crash", body="This PR resolves issue #42")
    assert heuristic_classify(pr) is None


def test_heuristic_classify_preserva_pr_original() -> None:
    pr = _pr(title="add OAuth support", body="")
    result = heuristic_classify(pr)
    assert result is not None
    assert result.pr is pr


def test_heuristic_classify_tipo_projeto_sempre_outro() -> None:
    # tipo de projeto depende do repo — heurística não tem dados suficientes
    pr = _pr(title="fix crash", body="")
    result = heuristic_classify(pr)
    assert result is not None
    assert result.project_type == "outro"


def test_heuristic_classify_feature_body_vazio() -> None:
    pr = _pr(title="implement dark mode", body="")
    result = heuristic_classify(pr)
    assert result is not None
    assert result.contribution_nature == "feature"


def test_heuristic_classify_doc_body_vazio() -> None:
    pr = _pr(title="update docs for API", body="")
    result = heuristic_classify(pr)
    assert result is not None
    assert result.contribution_nature == "documentação"


def test_heuristic_classify_refac_body_vazio() -> None:
    pr = _pr(title="refactor database layer", body="")
    result = heuristic_classify(pr)
    assert result is not None
    assert result.contribution_nature == "refatoração"


# ── heuristic_complexity ─────────────────────────────────────────────────────


def test_heuristic_complexity_zero_changes_retorna_low() -> None:
    pr = _pr()  # additions=0, deletions=0
    assert heuristic_complexity(pr) == "low"


def test_heuristic_complexity_grande_retorna_high() -> None:
    pr = _pr()._replace(additions=800, deletions=300)  # 1100 > 1000
    assert heuristic_complexity(pr) == "high"


def test_heuristic_complexity_muitos_arquivos_retorna_high() -> None:
    pr = _pr()._replace(additions=10, deletions=5, changed_files=25)
    assert heuristic_complexity(pr) == "high"


def test_heuristic_complexity_pequeno_retorna_low() -> None:
    pr = _pr()._replace(
        additions=10, deletions=15, changed_files=2
    )  # 25 < 30, files ≤ 2
    assert heuristic_complexity(pr) == "low"


def test_heuristic_complexity_medio_retorna_medium() -> None:
    pr = _pr()._replace(additions=100, deletions=50, changed_files=5)  # 150 < 300
    assert heuristic_complexity(pr) == "medium"


def test_heuristic_complexity_grande_sem_ultrapassar_1000_retorna_high() -> None:
    pr = _pr()._replace(additions=200, deletions=200, changed_files=5)  # 400 >= 300
    assert heuristic_complexity(pr) == "high"


def test_heuristic_complexity_retorna_valor_valido() -> None:
    from pr_analyzer.llm.classifiers import COMPLEXIDADES_REVISAO

    for additions, deletions, files in [
        (0, 0, 1),
        (10, 15, 2),
        (100, 50, 5),
        (800, 300, 10),
        (10, 5, 25),
    ]:
        pr = _pr()._replace(
            additions=additions, deletions=deletions, changed_files=files
        )
        assert heuristic_complexity(pr) in COMPLEXIDADES_REVISAO


# ── invariantes de propriedade ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "title",
    ["fix bug", "add feature", "refactor code", "update docs", "hotfix crash"],
)
def test_heuristic_nature_nunca_retorna_fora_do_frozenset(title: str) -> None:
    from pr_analyzer.llm.classifiers import NATUREZAS_CONTRIBUICAO

    result = heuristic_nature(title)
    if result is not None:
        assert result in NATUREZAS_CONTRIBUICAO


@pytest.mark.parametrize(
    ("title", "body"),
    [
        ("", ""),
        ("fix crash", ""),
        ("add feature", ""),
        ("update config", ""),
    ],
)
def test_heuristic_classify_valores_sempre_validos(title: str, body: str) -> None:
    from pr_analyzer.llm.classifiers import (
        NATUREZAS_CONTRIBUICAO,
        NIVEIS_CLAREZA_DESCRICAO,
        TIPOS_PROJETO,
    )

    pr = _pr(title=title, body=body)
    result = heuristic_classify(pr)
    if result is not None:
        assert result.project_type in TIPOS_PROJETO
        assert result.contribution_nature in NATUREZAS_CONTRIBUICAO
        assert result.description_clarity in NIVEIS_CLAREZA_DESCRICAO
