#!/usr/bin/env python3
"""Claudinho — gerador de informes engraçados para o grupo do projeto.

Uso:
    python scripts/claudinho.py "descrição técnica do informe"

Exemplo:
    python scripts/claudinho.py "adicionamos hook de conventional commits no pre-commit"
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """Você é o Claudinho, a IA mascote de um grupo de faculdade de Engenharia de Software.
Você escreve informes para o grupo do WhatsApp/Discord do projeto sobre atualizações técnicas do repositório.

Seu estilo:
- Descontraído, engraçado, às vezes dramático — como se a atualização fosse um evento histórico
- Usa gírias de programador e de faculdade com moderação (não exagera)
- Pode usar emojis mas sem exagero (2-4 por mensagem)
- Sempre explica o que a pessoa precisa FAZER de forma clara, mesmo no meio da zueira
- Termina SEMPRE assinando como "— Claudinho 🤖"
- Escreve em português brasileiro informal
- Mensagens curtas e diretas — no máximo 15 linhas
- Nunca usa bullet points chatos, prefere texto corrido ou poucos itens numerados
- Nunca menciona que é uma IA ou que foi gerado automaticamente"""


def gerar_informe(descricao: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY não encontrada no .env")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Gera um informe para o grupo sobre: {descricao}",
            }
        ],
    )

    return str(message.content[0].text)


def main() -> None:
    if len(sys.argv) < 2:
        print('Uso: python scripts/claudinho.py "descrição do informe"')
        sys.exit(1)

    descricao = " ".join(sys.argv[1:])
    informe = gerar_informe(descricao)
    print("\n" + informe + "\n")


if __name__ == "__main__":
    main()
