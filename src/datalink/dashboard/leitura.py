"""Leitura das marts para o painel, sem cálculo novo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datalink.domain.banco import Repositorio

CLIENTE_TODOS = "Todos"


@dataclass(frozen=True)
class Indicadores:
    """Tabelas marts já prontas para exibição."""

    resumo: dict[str, float]
    por_cidade: list[dict[str, Any]]
    por_cliente: list[dict[str, Any]]
    livros: list[dict[str, Any]]


def ler_marts(banco: Repositorio) -> Indicadores:
    """Lê somente as quatro tabelas marts."""
    return Indicadores(
        resumo=mapa_resumo(banco.listar("marts_resumo", limite=50)["linhas"]),
        por_cidade=banco.listar(
            "marts_vendas_cidade",
            limite=100,
            ordenar="receita_total",
            direcao="desc",
        )["linhas"],
        por_cliente=banco.listar(
            "marts_pedidos_cliente",
            limite=100,
            ordenar="cliente_nome",
            direcao="asc",
        )["linhas"],
        livros=banco.listar(
            "marts_livros_cliente",
            limite=200,
            ordenar="cliente_nome",
            direcao="asc",
        )["linhas"],
    )


def mapa_resumo(linhas: list[dict[str, Any]]) -> dict[str, float]:
    """Converte as linhas de marts_resumo em indicador para valor."""
    return {str(linha["indicador"]): float(linha["valor"]) for linha in linhas}


def filtrar_por_cliente(
    linhas: list[dict[str, Any]],
    cliente_nome: str,
) -> list[dict[str, Any]]:
    """Restringe a exibição a um cliente. `Todos` devolve a lista inteira."""
    if cliente_nome == CLIENTE_TODOS:
        return list(linhas)
    return [linha for linha in linhas if linha["cliente_nome"] == cliente_nome]
