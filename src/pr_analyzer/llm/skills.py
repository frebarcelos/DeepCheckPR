"""Skill definitions: system prompt e few-shot examples para modelos pequenos (tinyllama etc.).

Cada "skill" é um par (mensagem_usuario, resposta_assistente) que ensina o modelo
o formato JSON esperado antes de receber o input real. Modelos com <2B parâmetros
se beneficiam enormemente desses exemplos — o comportamento de seguir instruções
melhora sem precisar de fine-tuning.
"""

CLASSIFIER_SYSTEM_PROMPT: str = (
    "You are a strict JSON classifier for GitHub pull requests. "
    "Respond ONLY with a valid JSON object — no explanation, no markdown, no extra text. "
    "If unsure, pick the closest option from the list provided."
)

# Cada elemento é (user_input_exemplo, resposta_json_esperada).
# Os exemplos usam o mesmo formato de prompt que os classificadores geram,
# para que o modelo aprenda a mapear o padrão exato.

FEW_SHOT_PROJECT_TYPE: tuple[tuple[str, str], ...] = (
    (
        'Repositório: facebook/react. Títulos de PR: ["fix useState hook", "add memo API"].\n'
        'Responda estritamente em formato JSON: {"tipo_projeto": "..."}. '
        "Escolha uma das seguintes opções: aplicação web, biblioteca, ferramenta, framework, outro.",
        '{"tipo_projeto": "biblioteca"}',
    ),
    (
        'Repositório: django/django. Títulos de PR: ["fix ORM query", "add migration command"].\n'
        'Responda estritamente em formato JSON: {"tipo_projeto": "..."}. '
        "Escolha uma das seguintes opções: aplicação web, biblioteca, ferramenta, framework, outro.",
        '{"tipo_projeto": "framework"}',
    ),
)

FEW_SHOT_CONTRIBUTION_NATURE: tuple[tuple[str, str], ...] = (
    (
        "Título do PR: Fix NullPointerException in parser\n"
        "Corpo: Fixes crash when input is null.\n"
        'Responda estritamente em formato JSON: {"natureza": "..."}. '
        "Escolha uma das seguintes opções: bug fix, documentação, feature, outro, refatoração.",
        '{"natureza": "bug fix"}',
    ),
    (
        "Título do PR: Add dark mode support\n"
        "Corpo: Implements theme switching for the UI.\n"
        'Responda estritamente em formato JSON: {"natureza": "..."}. '
        "Escolha uma das seguintes opções: bug fix, documentação, feature, outro, refatoração.",
        '{"natureza": "feature"}',
    ),
)

FEW_SHOT_DESCRIPTION_CLARITY: tuple[tuple[str, str], ...] = (
    (
        "Avalie a clareza deste corpo de PR:\nFix bug\n"
        'Responda APENAS em JSON: {"clareza": "..."}. '
        "Opções válidas: básica, boa, excelente, insuficiente.",
        '{"clareza": "básica"}',
    ),
    (
        "Avalie a clareza deste corpo de PR:\n"
        "Fixes #123. Added null-check in parseInput() to prevent crash on empty string.\n"
        'Responda APENAS em JSON: {"clareza": "..."}. '
        "Opções válidas: básica, boa, excelente, insuficiente.",
        '{"clareza": "boa"}',
    ),
)
