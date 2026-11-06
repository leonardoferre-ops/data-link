from tests.fakes import BancoMemoria

from datalink.dashboard.leitura import CLIENTE_TODOS, filtrar_por_cliente, ler_marts


def _preparar(banco: BancoMemoria) -> None:
    banco.criar_tabela("marts_resumo", [])
    banco.inserir(
        "marts_resumo",
        [
            {"indicador": "qtd_pedidos", "valor": 2.0},
            {"indicador": "receita_total", "valor": 10.0},
        ],
    )
    banco.criar_tabela("marts_pedidos_cliente", [])
    banco.inserir(
        "marts_pedidos_cliente",
        [
            {"cliente_nome": "Bruno", "qtd_pedidos": 1},
            {"cliente_nome": "Ana", "qtd_pedidos": 2},
        ],
    )
    banco.criar_tabela("marts_livros_cliente", [])
    banco.inserir(
        "marts_livros_cliente",
        [
            {"cliente_nome": "Ana", "livro": "Dom"},
            {"cliente_nome": "Bruno", "livro": "Vidas"},
        ],
    )
    banco.criar_tabela("marts_vendas_cidade", [])
    banco.inserir(
        "marts_vendas_cidade",
        [
            {"cidade": "Recife", "receita_total": 10.0},
            {"cidade": "Salvador", "receita_total": 30.0},
        ],
    )


def test_ler_marts_ordena_e_mapeia_resumo() -> None:
    banco = BancoMemoria()
    _preparar(banco)
    indicadores = ler_marts(banco)
    assert indicadores.resumo["qtd_pedidos"] == 2.0
    assert [linha["cliente_nome"] for linha in indicadores.por_cliente] == [
        "Ana",
        "Bruno",
    ]
    assert indicadores.por_cidade[0]["cidade"] == "Salvador"


def test_filtrar_todos_um_cliente_e_lista_vazia() -> None:
    linhas = [{"cliente_nome": "Ana"}, {"cliente_nome": "Bruno"}]
    assert filtrar_por_cliente(linhas, CLIENTE_TODOS) == linhas
    assert filtrar_por_cliente(linhas, "Ana") == [{"cliente_nome": "Ana"}]
    assert filtrar_por_cliente([], "Ana") == []
