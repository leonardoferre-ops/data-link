"""Camada refined: limpa tipos e une pedidos com clientes via JOIN."""

from __future__ import annotations

from typing import Any

from cliente import Banco

from pipeline.util import recriar_tabela

COLUNAS_PEDIDOS_ENRIQUECIDOS = [
    {"nome": "pedido_id", "tipo": "inteiro", "obrigatorio": True},
    {"nome": "cliente_id", "tipo": "inteiro", "obrigatorio": True},
    {"nome": "cliente_nome", "tipo": "texto", "obrigatorio": True},
    {"nome": "cidade", "tipo": "texto", "obrigatorio": True},
    {"nome": "estado", "tipo": "texto", "obrigatorio": True},
    {"nome": "livro", "tipo": "texto", "obrigatorio": True},
    {"nome": "valor", "tipo": "decimal", "obrigatorio": True},
    {"nome": "data_pedido", "tipo": "texto", "obrigatorio": True},
]


def juntar_pedidos_clientes(
    pedidos: list[dict[str, Any]],
    clientes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Faz o JOIN lógico pedido.cliente_id = cliente.cliente_id e tipa o valor."""
    por_id = {int(cliente["cliente_id"]): cliente for cliente in clientes}
    enriquecidos: list[dict[str, Any]] = []
    for pedido in pedidos:
        cliente = por_id.get(int(pedido["cliente_id"]))
        if cliente is None:
            continue
        enriquecidos.append(
            {
                "pedido_id": int(pedido["pedido_id"]),
                "cliente_id": int(pedido["cliente_id"]),
                "cliente_nome": str(cliente["nome"]).strip(),
                "cidade": str(cliente["cidade"]).strip(),
                "estado": str(cliente["estado"]).strip().upper(),
                "livro": str(pedido["livro"]).strip(),
                "valor": float(pedido["valor"]),
                "data_pedido": str(pedido["data_pedido"]).strip(),
            }
        )
    return enriquecidos


def carregar_refined(banco: Banco) -> dict[str, int]:
    """Lê a raw, aplica o JOIN e grava refined_pedidos."""
    clientes = banco.listar("raw_clientes", limite=500)["linhas"]
    pedidos = banco.listar("raw_pedidos", limite=500)["linhas"]
    enriquecidos = juntar_pedidos_clientes(pedidos, clientes)

    recriar_tabela(banco, "refined_pedidos", COLUNAS_PEDIDOS_ENRIQUECIDOS)
    if enriquecidos:
        banco.inserir("refined_pedidos", enriquecidos)
    return {"refined_pedidos": len(enriquecidos)}


def main() -> None:
    with Banco() as banco:
        contagem = carregar_refined(banco)
        print(f"Camada refined carregada: {contagem}")


if __name__ == "__main__":
    main()
