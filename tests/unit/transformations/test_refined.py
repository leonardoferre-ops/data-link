import pytest

from datalink.transformations.refined import conformar_pedido


def test_conforma_pedido_com_espaco_e_estado_minusculo() -> None:
    pedido = {
        "pedido_id": 1,
        "cliente_id": 10,
        "livro": " Dom Casmurro ",
        "valor": "42.90",
        "data_pedido": " 2024-01-10 ",
    }
    cliente = {"cliente_id": 10, "nome": " Ana ", "cidade": " Recife ", "estado": "pe"}
    linha = conformar_pedido(pedido, cliente)
    assert linha["cliente_nome"] == "Ana"
    assert linha["cidade"] == "Recife"
    assert linha["estado"] == "PE"
    assert linha["livro"] == "Dom Casmurro"
    assert linha["valor"] == 42.90
    assert linha["data_pedido"] == "2024-01-10"


def test_rejeita_valor_invalido_bool_e_nao_finito() -> None:
    pedido = {
        "pedido_id": 4,
        "cliente_id": 1,
        "livro": "A",
        "data_pedido": "2024-01-01",
    }
    cliente = {"nome": "Ana", "cidade": "Recife", "estado": "PE"}
    with pytest.raises(ValueError, match="Valor inválido"):
        conformar_pedido({**pedido, "valor": "abc"}, cliente)
    with pytest.raises(ValueError, match="Valor inválido"):
        conformar_pedido({**pedido, "valor": True}, cliente)
    with pytest.raises(ValueError, match="Valor inválido"):
        conformar_pedido({**pedido, "valor": float("nan")}, cliente)


def test_um_pedido_decimal_inteiro() -> None:
    linha = conformar_pedido(
        {
            "pedido_id": "8",
            "cliente_id": "1",
            "livro": "Único",
            "valor": 10,
            "data_pedido": "2024-05-01",
        },
        {"nome": "Ana", "cidade": "Recife", "estado": "pe"},
    )
    assert linha["pedido_id"] == 8
    assert linha["valor"] == 10.0
