"""Indicadores prontos para o painel, calculados fora da tela."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def vendas_por_cidade(pedidos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrega receita e ticket médio por cidade e estado."""
    grupos: dict[tuple[str, str], list[float]] = defaultdict(list)
    for pedido in pedidos:
        chave = (str(pedido["cidade"]), str(pedido["estado"]))
        grupos[chave].append(float(pedido["valor"]))

    linhas: list[dict[str, Any]] = []
    for (cidade, estado), valores in sorted(grupos.items()):
        receita = round(sum(valores), 2)
        qtd = len(valores)
        linhas.append(
            {
                "cidade": cidade,
                "estado": estado,
                "qtd_pedidos": qtd,
                "receita_total": receita,
                "ticket_medio": round(receita / qtd, 2),
            }
        )
    return linhas


def resumo_indicadores(pedidos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calcula quantidade, clientes, receita e ticket médio do lote."""
    if not pedidos:
        return _resumo_vazio()

    valores = [float(pedido["valor"]) for pedido in pedidos]
    clientes = {int(pedido["cliente_id"]) for pedido in pedidos}
    receita = round(sum(valores), 2)
    return [
        {"indicador": "qtd_pedidos", "valor": float(len(valores))},
        {"indicador": "qtd_clientes", "valor": float(len(clientes))},
        {"indicador": "receita_total", "valor": receita},
        {"indicador": "ticket_medio", "valor": round(receita / len(valores), 2)},
    ]


def pedidos_por_cliente(pedidos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrega quantidade, receita e ticket médio por cliente."""
    grupos: dict[int, dict[str, Any]] = {}
    for pedido in pedidos:
        cliente_id = int(pedido["cliente_id"])
        if cliente_id not in grupos:
            grupos[cliente_id] = {
                "cliente_id": cliente_id,
                "cliente_nome": str(pedido["cliente_nome"]),
                "cidade": str(pedido["cidade"]),
                "estado": str(pedido["estado"]),
                "valores": [],
            }
        grupos[cliente_id]["valores"].append(float(pedido["valor"]))

    linhas: list[dict[str, Any]] = []
    for cliente_id, dados in sorted(
        grupos.items(), key=lambda item: item[1]["cliente_nome"]
    ):
        valores = dados["valores"]
        receita = round(sum(valores), 2)
        qtd = len(valores)
        linhas.append(
            {
                "cliente_id": cliente_id,
                "cliente_nome": dados["cliente_nome"],
                "cidade": dados["cidade"],
                "estado": dados["estado"],
                "qtd_pedidos": qtd,
                "receita_total": receita,
                "ticket_medio": round(receita / qtd, 2),
            }
        )
    return linhas


def livros_por_cliente(pedidos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lista cada livro comprado, um pedido por linha."""
    linhas = [
        {
            "pedido_id": int(pedido["pedido_id"]),
            "cliente_id": int(pedido["cliente_id"]),
            "cliente_nome": str(pedido["cliente_nome"]),
            "livro": str(pedido["livro"]),
            "valor": float(pedido["valor"]),
            "data_pedido": str(pedido["data_pedido"]),
        }
        for pedido in pedidos
    ]
    return sorted(linhas, key=lambda item: (item["cliente_nome"], item["data_pedido"]))


def _resumo_vazio() -> list[dict[str, Any]]:
    return [
        {"indicador": "qtd_pedidos", "valor": 0.0},
        {"indicador": "qtd_clientes", "valor": 0.0},
        {"indicador": "receita_total", "valor": 0.0},
        {"indicador": "ticket_medio", "valor": 0.0},
    ]
