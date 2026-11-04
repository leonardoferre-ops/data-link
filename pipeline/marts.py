"""Camada marts: indicadores prontos para o dashboard (sem cálculo na tela)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from cliente import Banco

from pipeline.util import recriar_tabela

COLUNAS_VENDAS_CIDADE = [
    {"nome": "cidade", "tipo": "texto", "obrigatorio": True},
    {"nome": "estado", "tipo": "texto", "obrigatorio": True},
    {"nome": "qtd_pedidos", "tipo": "inteiro", "obrigatorio": True},
    {"nome": "receita_total", "tipo": "decimal", "obrigatorio": True},
    {"nome": "ticket_medio", "tipo": "decimal", "obrigatorio": True},
]

COLUNAS_RESUMO = [
    {"nome": "indicador", "tipo": "texto", "obrigatorio": True},
    {"nome": "valor", "tipo": "decimal", "obrigatorio": True},
]

COLUNAS_PEDIDOS_CLIENTE = [
    {"nome": "cliente_id", "tipo": "inteiro", "obrigatorio": True},
    {"nome": "cliente_nome", "tipo": "texto", "obrigatorio": True},
    {"nome": "cidade", "tipo": "texto", "obrigatorio": True},
    {"nome": "estado", "tipo": "texto", "obrigatorio": True},
    {"nome": "qtd_pedidos", "tipo": "inteiro", "obrigatorio": True},
    {"nome": "receita_total", "tipo": "decimal", "obrigatorio": True},
    {"nome": "ticket_medio", "tipo": "decimal", "obrigatorio": True},
]

COLUNAS_LIVROS_CLIENTE = [
    {"nome": "pedido_id", "tipo": "inteiro", "obrigatorio": True},
    {"nome": "cliente_id", "tipo": "inteiro", "obrigatorio": True},
    {"nome": "cliente_nome", "tipo": "texto", "obrigatorio": True},
    {"nome": "livro", "tipo": "texto", "obrigatorio": True},
    {"nome": "valor", "tipo": "decimal", "obrigatorio": True},
    {"nome": "data_pedido", "tipo": "texto", "obrigatorio": True},
]


def vendas_por_cidade(pedidos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrega receita e ticket médio por cidade a partir dos pedidos refined."""
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
                "ticket_medio": round(receita / qtd, 2) if qtd else 0.0,
            }
        )
    return linhas


def resumo_indicadores(pedidos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calcula indicadores gerais já prontos para exibição."""
    if not pedidos:
        return [
            {"indicador": "qtd_pedidos", "valor": 0.0},
            {"indicador": "qtd_clientes", "valor": 0.0},
            {"indicador": "receita_total", "valor": 0.0},
            {"indicador": "ticket_medio", "valor": 0.0},
        ]

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
    for cliente_id, dados in sorted(grupos.items(), key=lambda item: item[1]["cliente_nome"]):
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
                "ticket_medio": round(receita / qtd, 2) if qtd else 0.0,
            }
        )
    return linhas


def livros_por_cliente(pedidos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lista cada livro comprado por cliente (um pedido por linha)."""
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


def carregar_marts(banco: Banco) -> dict[str, int]:
    """Lê refined_pedidos e materializa as tabelas de indicadores."""
    pedidos = banco.listar("refined_pedidos", limite=500)["linhas"]
    por_cidade = vendas_por_cidade(pedidos)
    por_cliente = pedidos_por_cliente(pedidos)
    livros = livros_por_cliente(pedidos)
    resumo = resumo_indicadores(pedidos)

    recriar_tabela(banco, "marts_vendas_cidade", COLUNAS_VENDAS_CIDADE)
    recriar_tabela(banco, "marts_pedidos_cliente", COLUNAS_PEDIDOS_CLIENTE)
    recriar_tabela(banco, "marts_livros_cliente", COLUNAS_LIVROS_CLIENTE)
    recriar_tabela(banco, "marts_resumo", COLUNAS_RESUMO)

    if por_cidade:
        banco.inserir("marts_vendas_cidade", por_cidade)
    if por_cliente:
        banco.inserir("marts_pedidos_cliente", por_cliente)
    if livros:
        banco.inserir("marts_livros_cliente", livros)
    if resumo:
        banco.inserir("marts_resumo", resumo)

    return {
        "marts_vendas_cidade": len(por_cidade),
        "marts_pedidos_cliente": len(por_cliente),
        "marts_livros_cliente": len(livros),
        "marts_resumo": len(resumo),
    }


def main() -> None:
    with Banco() as banco:
        contagem = carregar_marts(banco)
        print(f"Camada marts carregada: {contagem}")


if __name__ == "__main__":
    main()
