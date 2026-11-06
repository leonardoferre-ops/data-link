from datalink.transformations.marts import (
    livros_por_cliente,
    pedidos_por_cliente,
    resumo_indicadores,
    vendas_por_cidade,
)


def test_vendas_por_cidade_calcula_ticket_medio() -> None:
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


def test_vendas_e_livros_vazios() -> None:
    assert vendas_por_cidade([]) == []
    assert livros_por_cliente([]) == []
    assert pedidos_por_cliente([]) == []


def test_resumo_indicadores_com_lista_vazia() -> None:
    resultado = {item["indicador"]: item["valor"] for item in resumo_indicadores([])}
    assert resultado["qtd_pedidos"] == 0.0
    assert resultado["qtd_clientes"] == 0.0
    assert resultado["receita_total"] == 0.0
    assert resultado["ticket_medio"] == 0.0


def test_resumo_indicadores_agrega_pedidos_inventados() -> None:
    pedidos = [
        {"cliente_id": 1, "valor": 10.0},
        {"cliente_id": 1, "valor": 30.0},
        {"cliente_id": 2, "valor": 20.0},
    ]
    resultado = {
        item["indicador"]: item["valor"] for item in resumo_indicadores(pedidos)
    }
    assert resultado["qtd_pedidos"] == 3.0
    assert resultado["qtd_clientes"] == 2.0
    assert resultado["receita_total"] == 60.0
    assert resultado["ticket_medio"] == 20.0


def test_resumo_de_um_pedido() -> None:
    resultado = {
        item["indicador"]: item["valor"]
        for item in resumo_indicadores([{"cliente_id": 1, "valor": 15.0}])
    }
    assert resultado["qtd_pedidos"] == 1.0
    assert resultado["ticket_medio"] == 15.0


def test_pedidos_por_cliente_agrega_quantidade_e_receita() -> None:
    pedidos = [
        {
            "cliente_id": 2,
            "cliente_nome": "Bruno",
            "cidade": "Salvador",
            "estado": "BA",
            "valor": 30.0,
        },
        {
            "cliente_id": 1,
            "cliente_nome": "Ana",
            "cidade": "Recife",
            "estado": "PE",
            "valor": 40.0,
        },
        {
            "cliente_id": 1,
            "cliente_nome": "Ana",
            "cidade": "Recife",
            "estado": "PE",
            "valor": 60.0,
        },
    ]
    resultado = pedidos_por_cliente(pedidos)
    por_nome = {linha["cliente_nome"]: linha for linha in resultado}
    assert [linha["cliente_nome"] for linha in resultado] == ["Ana", "Bruno"]
    assert por_nome["Ana"]["qtd_pedidos"] == 2
    assert por_nome["Ana"]["receita_total"] == 100.0
    assert por_nome["Ana"]["ticket_medio"] == 50.0
    assert por_nome["Bruno"]["qtd_pedidos"] == 1
    assert por_nome["Bruno"]["receita_total"] == 30.0


def test_livros_por_cliente_lista_titulo_comprado() -> None:
    pedidos = [
        {
            "pedido_id": 2,
            "cliente_id": 1,
            "cliente_nome": "Ana",
            "livro": "Vidas Secas",
            "valor": 33.0,
            "data_pedido": "2024-02-05",
        },
        {
            "pedido_id": 1,
            "cliente_id": 1,
            "cliente_nome": "Ana",
            "livro": "Dom Casmurro",
            "valor": 42.9,
            "data_pedido": "2024-01-10",
        },
    ]
    resultado = livros_por_cliente(pedidos)
    assert [linha["livro"] for linha in resultado] == ["Dom Casmurro", "Vidas Secas"]
    assert resultado[0]["cliente_nome"] == "Ana"
    assert resultado[0]["valor"] == 42.9
