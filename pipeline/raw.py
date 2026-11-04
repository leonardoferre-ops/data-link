"""Camada raw: carrega o dado bruto sem alterar valores."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from cliente import Banco

from pipeline.util import recriar_tabela

RAIZ = Path(__file__).resolve().parents[1]
DIR_BRUTO = RAIZ / "dados" / "bruto"

COLUNAS_CLIENTES = [
    {"nome": "cliente_id", "tipo": "inteiro", "obrigatorio": True},
    {"nome": "nome", "tipo": "texto", "obrigatorio": True},
    {"nome": "cidade", "tipo": "texto", "obrigatorio": True},
    {"nome": "estado", "tipo": "texto", "obrigatorio": True},
]

COLUNAS_PEDIDOS = [
    {"nome": "pedido_id", "tipo": "inteiro", "obrigatorio": True},
    {"nome": "cliente_id", "tipo": "inteiro", "obrigatorio": True},
    {"nome": "livro", "tipo": "texto", "obrigatorio": True},
    {"nome": "valor", "tipo": "texto", "obrigatorio": True},
    {"nome": "data_pedido", "tipo": "texto", "obrigatorio": True},
]


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    """Lê o CSV e devolve as linhas exatamente como estão no arquivo."""
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def carregar_raw(banco: Banco, diretorio: Path | None = None) -> dict[str, int]:
    """Grava clientes e pedidos na camada raw sem transformar os valores."""
    origem = diretorio or DIR_BRUTO
    clientes = ler_csv(origem / "clientes.csv")
    pedidos = ler_csv(origem / "pedidos.csv")

    recriar_tabela(banco, "raw_clientes", COLUNAS_CLIENTES)
    recriar_tabela(banco, "raw_pedidos", COLUNAS_PEDIDOS)

    # Mantém o texto bruto (ex.: valor como string) — nada é alterado.
    banco.inserir(
        "raw_clientes",
        [
            {
                "cliente_id": int(linha["cliente_id"]),
                "nome": linha["nome"],
                "cidade": linha["cidade"],
                "estado": linha["estado"],
            }
            for linha in clientes
        ],
    )
    banco.inserir(
        "raw_pedidos",
        [
            {
                "pedido_id": int(linha["pedido_id"]),
                "cliente_id": int(linha["cliente_id"]),
                "livro": linha["livro"],
                "valor": linha["valor"],
                "data_pedido": linha["data_pedido"],
            }
            for linha in pedidos
        ],
    )
    return {"raw_clientes": len(clientes), "raw_pedidos": len(pedidos)}


def main() -> None:
    with Banco() as banco:
        contagem = carregar_raw(banco)
        print(f"Camada raw carregada: {contagem}")


if __name__ == "__main__":
    main()
