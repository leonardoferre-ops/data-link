"""Painel que lê somente a camada marts — nenhum cálculo na tela."""

from __future__ import annotations

import streamlit as st

from cliente import Banco, ErroBanco


def _mapa_resumo(linhas: list[dict]) -> dict[str, float]:
    return {linha["indicador"]: float(linha["valor"]) for linha in linhas}


def main() -> None:
    st.set_page_config(page_title="Indicadores de pedidos", layout="wide")
    st.title("Indicadores de pedidos")
    st.caption("Fonte: camada marts (sem cálculo nesta tela).")

    try:
        with Banco() as banco:
            resumo = banco.listar("marts_resumo", limite=50)["linhas"]
            por_cidade = banco.listar(
                "marts_vendas_cidade",
                limite=100,
                ordenar="receita_total",
                direcao="desc",
            )["linhas"]
    except ErroBanco as exc:
        st.error(
            "Não foi possível ler os indicadores. "
            "Suba a API e rode `python -m pipeline.executar` antes. "
            f"Detalhe: {exc}"
        )
        return

    indicadores = _mapa_resumo(resumo)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pedidos", int(indicadores.get("qtd_pedidos", 0)))
    col2.metric("Clientes", int(indicadores.get("qtd_clientes", 0)))
    col3.metric("Receita total", f"R$ {indicadores.get('receita_total', 0):.2f}")
    col4.metric("Ticket médio", f"R$ {indicadores.get('ticket_medio', 0):.2f}")

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
        {
            linha["cidade"]: linha["receita_total"]
            for linha in por_cidade
        },
        alt="Receita total por cidade a partir de marts_vendas_cidade",
    )


if __name__ == "__main__":
    main()
