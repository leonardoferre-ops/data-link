"""Painel que lê somente a camada marts."""

from __future__ import annotations

import streamlit as st

from datalink.config.ambiente import url_da_api
from datalink.dashboard.leitura import CLIENTE_TODOS, filtrar_por_cliente, ler_marts
from datalink.infrastructure.cliente import Banco, ErroBanco


def main() -> None:
    """Abre o painel de indicadores a partir das tabelas marts."""
    st.set_page_config(page_title="Indicadores de pedidos", layout="wide")
    st.title("Indicadores de pedidos")
    st.caption("Fonte: camada marts (sem cálculo nesta tela).")
    try:
        with Banco(url_da_api()) as banco:
            indicadores = ler_marts(banco)
    except ErroBanco as exc:
        st.error(_mensagem_falha(exc))
        return
    _resumo(indicadores.resumo)
    _clientes(indicadores.por_cliente, indicadores.livros)
    _cidades(indicadores.por_cidade)


def _mensagem_falha(exc: ErroBanco) -> str:
    return (
        "Não foi possível ler os indicadores. "
        "Suba a API e rode `poetry run python -m datalink` antes. "
        f"Detalhe: {exc}"
    )


def _resumo(indicadores: dict[str, float]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pedidos", int(indicadores.get("qtd_pedidos", 0)))
    col2.metric("Clientes", int(indicadores.get("qtd_clientes", 0)))
    col3.metric("Receita total", f"R$ {indicadores.get('receita_total', 0):.2f}")
    col4.metric("Ticket médio", f"R$ {indicadores.get('ticket_medio', 0):.2f}")


def _clientes(por_cliente: list[dict], livros: list[dict]) -> None:
    st.subheader("Pedidos por cliente")
    if not por_cliente:
        st.info("A tabela marts_pedidos_cliente está vazia.")
        return
    nomes = [CLIENTE_TODOS, *[linha["cliente_nome"] for linha in por_cliente]]
    escolhido = st.selectbox("Cliente", options=nomes)
    _tabela_clientes(filtrar_por_cliente(por_cliente, escolhido))
    _tabela_livros(filtrar_por_cliente(livros, escolhido))
    st.bar_chart(
        {linha["cliente_nome"]: linha["qtd_pedidos"] for linha in por_cliente},
        alt="Quantidade de pedidos por cliente a partir de marts_pedidos_cliente",
    )


def _tabela_clientes(linhas: list[dict]) -> None:
    st.dataframe(
        [
            {
                "cliente": linha["cliente_nome"],
                "cidade": linha["cidade"],
                "estado": linha["estado"],
                "qtd_pedidos": linha["qtd_pedidos"],
                "receita_total": linha["receita_total"],
                "ticket_medio": linha["ticket_medio"],
            }
            for linha in linhas
        ],
        width="stretch",
        hide_index=True,
        alt="Pedidos agregados por cliente a partir de marts_pedidos_cliente",
    )


def _tabela_livros(linhas: list[dict]) -> None:
    st.markdown("**Livros comprados**")
    if not linhas:
        st.info("Nenhum livro listado em marts_livros_cliente.")
        return
    st.dataframe(
        [
            {
                "cliente": linha["cliente_nome"],
                "livro": linha["livro"],
                "valor": linha["valor"],
                "data_pedido": linha["data_pedido"],
            }
            for linha in linhas
        ],
        width="stretch",
        hide_index=True,
        alt="Livros comprados por cliente a partir de marts_livros_cliente",
    )


def _cidades(por_cidade: list[dict]) -> None:
    st.subheader("Vendas por cidade")
    if not por_cidade:
        st.info("A tabela marts_vendas_cidade está vazia.")
        return
    st.dataframe(
        [
            {
                "cidade": linha["cidade"],
                "estado": linha["estado"],
                "qtd_pedidos": linha["qtd_pedidos"],
                "receita_total": linha["receita_total"],
                "ticket_medio": linha["ticket_medio"],
            }
            for linha in por_cidade
        ],
        width="stretch",
        hide_index=True,
        alt="Tabela de vendas por cidade vinda de marts_vendas_cidade",
    )
    st.bar_chart(
        {linha["cidade"]: linha["receita_total"] for linha in por_cidade},
        alt="Receita total por cidade a partir de marts_vendas_cidade",
    )


if __name__ == "__main__":
    main()
