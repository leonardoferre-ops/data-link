"""Consultas de exemplo contra a API local.

Rode a API antes:

    uvicorn app.main:app --host 127.0.0.1 --port 8741
    python exemplos/consultas.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cliente import Banco, ErroBanco


def mostrar(titulo: str, linhas: list[dict]) -> None:
    print(f"\n{titulo}")
    if not linhas:
        print("  (nenhuma linha)")
        return
    for linha in linhas:
        partes = [f"{chave}: {valor}" for chave, valor in linha.items() if chave != "criado_em"]
        print("  - " + " | ".join(partes))


def main() -> None:
    with Banco() as banco:
        saude = banco.saude()
        print(f"API no ar ({saude['banco']}).")

        baratos = banco.consultar(
            "livros",
            colunas=["titulo", "autor", "ano", "preco"],
            filtros=[
                {"coluna": "preco", "op": "menor", "valor": 40},
                {"coluna": "genero", "op": "igual", "valor": "romance"},
            ],
            ordenar=[{"coluna": "preco", "direcao": "asc"}],
        )
        mostrar(
            f"Romances abaixo de R$ 40 ({baratos['total']} no total)",
            baratos["linhas"],
        )

        por_autor = banco.sql(
            """
            SELECT autor, COUNT(*) AS quantidade, ROUND(AVG(preco), 2) AS preco_medio
            FROM livros
            GROUP BY autor
            ORDER BY quantidade DESC, autor
            """
        )
        mostrar("Livros por autor", por_autor["linhas"])

        um = banco.sql(
            "SELECT titulo, ano FROM livros WHERE autor = ? ORDER BY ano",
            ["Machado de Assis"],
        )
        mostrar("Machado de Assis", um["linhas"])

        try:
            banco.criar_tabela(
                "contatos",
                [
                    {"nome": "nome", "tipo": "texto", "obrigatorio": True},
                    {"nome": "cidade", "tipo": "texto", "obrigatorio": True},
                    {"nome": "ativo", "tipo": "booleano", "obrigatorio": True},
                ],
            )
            print("\nTabela contatos criada.")
        except ErroBanco as exc:
            if exc.status != 409:
                raise
            print("\nTabela contatos já existia.")

        gravados = banco.inserir(
            "contatos",
            {"nome": "Lia Nunes", "cidade": "Salvador", "ativo": True},
        )
        print(f"Contato gravado com id {gravados[0]['id']}.")
        ativos = banco.listar("contatos", ativo=True, ordenar="nome")
        mostrar(f"Contatos ativos ({ativos['total']})", ativos["linhas"])


if __name__ == "__main__":
    try:
        main()
    except ErroBanco as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
