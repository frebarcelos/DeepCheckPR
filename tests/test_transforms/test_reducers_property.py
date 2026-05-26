"""
Testes baseados em propriedades para os transformadores e filtros.

Este módulo utiliza a biblioteca Hypothesis para verificar invariantes e
propriedades matemáticas das funções de redução, agregação e filtros de PRs.
"""

from hypothesis import given
from hypothesis import strategies as st

from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.transforms.filters import by_language, with_non_empty_body
from pr_analyzer.transforms.mappers import PRStats
from pr_analyzer.transforms.reducers import aggregate_stats, count_by_language

pr_record_strategy = st.builds(
    PRRecord,
    pr_id=st.one_of(st.none(), st.integers()),
    repo_name=st.text(),
    language=st.text(),
    title=st.text(),
    body=st.text(),
    state=st.text(),
    created_at=st.text(),
    merged_at=st.text(),
    additions=st.one_of(st.none(), st.integers(min_value=0)),
    deletions=st.one_of(st.none(), st.integers(min_value=0)),
    changed_files=st.one_of(st.none(), st.integers(min_value=0)),
)

pr_stats_strategy = st.builds(
    PRStats,
    body_char_count=st.integers(min_value=0),
    body_word_count=st.integers(min_value=0),
    total_changes=st.integers(min_value=0),
    is_merged=st.booleans(),
)


@given(st.lists(pr_record_strategy), st.lists(pr_record_strategy))
def test_count_by_language_concatenation(list1, list2):
    """
    Testa a propriedade de que a contagem por linguagem de duas listas concatenadas
    é igual à soma dos resultados individuais de cada lista.

    Args:
        list1 (list[PRRecord]): A primeira lista de registros de pull requests.
        list2 (list[PRRecord]): A segunda lista de registros de pull requests.
    """
    res1 = count_by_language(list1)
    res2 = count_by_language(list2)
    res_combined = count_by_language(list1 + list2)

    all_keys = frozenset(res1.keys()) | frozenset(res2.keys())
    expected = {lang: res1.get(lang, 0) + res2.get(lang, 0) for lang in all_keys}

    assert res_combined == expected


@given(pr_stats_strategy)
def test_aggregate_stats_single_element(stat):
    """
    Testa a propriedade de que a agregação de estatísticas para um único
    elemento retorna exatamente as métricas desse elemento.

    Args:
        stat (PRStats): Um objeto contendo as estatísticas de um pull request.
    """
    result = aggregate_stats([stat])
    assert result["avg_chars"] == float(stat.body_char_count)
    assert result["avg_words"] == float(stat.body_word_count)
    assert result["avg_changes"] == float(stat.total_changes)
    assert result["merge_rate"] == (1.0 if stat.is_merged else 0.0)


@given(st.lists(pr_record_strategy), st.text())
def test_filter_by_language_idempotent(prs, lang):
    """
    Testa a propriedade de idempotência do filtro por linguagem, garantindo que
    aplicá-lo duas vezes resulta na mesma saída de aplicá-lo apenas uma vez.

    Args:
        prs (list[PRRecord]): Uma lista de registros de pull requests.
        lang (str): A linguagem de programação a ser filtrada.
    """
    predicate = by_language(lang)
    first_pass = list(filter(predicate, prs))
    second_pass = list(filter(predicate, first_pass))
    assert first_pass == second_pass


@given(st.lists(pr_record_strategy))
def test_filter_non_empty_body_idempotent(prs):
    """
    Testa a propriedade de idempotência do filtro de corpo não vazio, garantindo que
    aplicá-lo duas vezes resulta na mesma saída de aplicá-lo apenas uma vez.

    Args:
        prs (list[PRRecord]): Uma lista de registros de pull requests.
    """
    predicate = with_non_empty_body()
    first_pass = list(filter(predicate, prs))
    second_pass = list(filter(predicate, first_pass))
    assert first_pass == second_pass
