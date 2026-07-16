# Contribuindo com o DeepCheckPR

Obrigado pelo interesse em contribuir. O DeepCheckPR preserva a autoria
coletiva do projeto original e recebe melhorias por Pull Request.

## Ambiente

```bash
python -m venv .venv
pip install -e ".[dev]"
pre-commit install
pre-commit install --hook-type commit-msg
pre-commit install --hook-type pre-push
```

No Windows PowerShell, execute os binários pelo diretório
`.venv\Scripts\` caso o ambiente não esteja ativado.

## Fluxo de contribuição

1. Crie uma branch a partir de `develop`.
2. Escreva ou atualize os testes antes da implementação.
3. Mantenha a alteração pequena e focada.
4. Execute as verificações locais.
5. Use Conventional Commits.
6. Abra um Pull Request para `develop`.

Exemplo de commit:

```text
fix(cache): evita reclassificação após cache hit
```

## Verificações obrigatórias

```bash
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
mypy --no-site-packages src/
python -X utf8 scripts/check_paradigm.py
pytest tests/ -m "not integration" --cov-fail-under=80
```

## Regras funcionais

Os módulos `transforms/` e `pipeline/` são puros:

- não use loops `for` ou `while`;
- não faça mutação por índice nem use métodos mutantes;
- não realize I/O;
- prefira `map`, `filter`, `reduce`, expressões geradoras e estruturas
  imutáveis.

Efeitos colaterais pertencem a `io/`, `cache/`, `llm/` ou `ui/`, conforme a
responsabilidade da operação.

## Uso responsável de ferramentas de IA

Ferramentas de IA são opcionais e nenhuma marca ou provedor é exigido. Ao
utilizá-las:

- não envie chaves, tokens, dados privados ou datasets restritos;
- revise cada alteração antes de submetê-la;
- confirme licenças e procedência de código sugerido;
- execute toda a suíte de testes e as verificações estáticas;
- descreva no Pull Request qualquer uso material de código gerado;
- assuma responsabilidade técnica pelo resultado final.

Configurações pessoais de assistentes e editores não devem ser versionadas.

## Autoria

Não remova créditos existentes nem atribua módulos inteiros a uma única pessoa
sem evidência no histórico. Novas contribuições permanecem registradas nos
commits e no histórico de Pull Requests.
