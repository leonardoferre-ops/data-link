"""Testes unitários das transformações com dados inventados (sem banco do projeto)."""

from pipeline.marts import resumo_indicadores, vendas_por_cidade
from pipeline.refined import juntar_pedidos_clientes


def test_join_enriquece_pedido_com_cliente():
    clientes = [
        {"cliente_id": 10, "nome": " Ana ", "cidade": " Recife ", "estado": "pe"},
        {"cliente_id": 20, "nome": "Bruno", "cidade": "Salvador", "estado": "BA"},
    ]
    pedidos = [
        {
            "pedido_id": 1,
            "cliente_id": 10,
            "livro": " Dom Casmurro ",
            "valor": "42.90",
            "data_pedido": "2024-01-10",
        },
        {
            "pedido_id": 2,
            "cliente_id": 99,
            "livro": "Inexistente",
            "valor": "10.00",
            "data_pedido": "2024-01-11",
        },
    ]

    resultado = juntar_pedidos_clientes(pedidos, clientes)

    assert len(resultado) == 1
    linha = resultado[0]
    assert linha["pedido_id"] == 1
    assert linha["cliente_nome"] == "Ana"
    assert linha["cidade"] == "Recife"
    assert linha["estado"] == "PE"
    assert linha["livro"] == "Dom Casmurro"
    assert linha["valor"] == 42.90


def test_vendas_por_cidade_calcula_ticket_medio():
    pedidos = [
        {"cidade": "Recife", "estado": "PE", "valor": 40.0},
        {"cidade": "Recife", "estado": "PE", "valor": 60.0},
        {"cidade": "Salvador", "estado": "BA", "valor": 30.0},
    ]

    resultado = vendas_por_cidade(pedidos)

    por_cidade = {linha["cidade"]: linha for linha in resultado}
    assert por_cidade["Recife"]["qtd_pedidos"] == 2
    assert por_cidade["Recife"]["receita_total"] == 100.0
    assert por_cidade["Recife"]["ticket_medio"] == 50.0
    assert por_cidade["Salvador"]["qtd_pedidos"] == 1
    assert por_cidade["Salvador"]["ticket_medio"] == 30.0


def test_resumo_indicadores_com_lista_vazia():
    resultado = {item["indicador"]: item["valor"] for item in resumo_indicadores([])}
    assert resultado["qtd_pedidos"] == 0.0
    assert resultado["receita_total"] == 0.0
    assert resultado["ticket_medio"] == 0.0


def test_resumo_indicadores_agrega_pedidos_inventados():
    pedidos = [
        {"cliente_id": 1, "valor": 10.0},
        {"cliente_id": 1, "valor": 30.0},
        {"cliente_id": 2, "valor": 20.0},
    ]

    resultado = {item["indicador"]: item["valor"] for item in resumo_indicadores(pedidos)}

    assert resultado["qtd_pedidos"] == 3.0
    assert resultado["qtd_clientes"] == 2.0
    assert resultado["receita_total"] == 60.0
    assert resultado["ticket_medio"] == 20.0
