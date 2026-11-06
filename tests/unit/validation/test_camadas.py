import pytest

from datalink.domain.contratos import CAMPOS_CLIENTES_RAW, CAMPOS_PEDIDOS_RAW, Campo
from datalink.validation.camadas import (
    coagir,
    rejeitar_pedidos_sem_cliente,
    validar_lote,
)


def _cliente(cliente_id: str = "1", nome: str = "Ana") -> dict[str, str]:
    return {
        "cliente_id": cliente_id,
        "nome": nome,
        "cidade": "Recife",
        "estado": "PE",
    }


def test_aceita_cliente_valido_e_converte_id() -> None:
    lote = validar_lote([_cliente()], CAMPOS_CLIENTES_RAW, chaves=("cliente_id",))
    assert lote.rejeitados == ()
    assert lote.aceitos[0]["cliente_id"] == 1
    assert lote.aceitos[0]["nome"] == "Ana"


def test_preserva_espacos_do_texto_bruto() -> None:
    linha = _cliente(nome=" Ana ")
    lote = validar_lote([linha], CAMPOS_CLIENTES_RAW, chaves=("cliente_id",))
    assert lote.aceitos[0]["nome"] == " Ana "


def test_rejeita_lote_vazio() -> None:
    lote = validar_lote([], CAMPOS_CLIENTES_RAW, chaves=("cliente_id",))
    assert lote.aceitos == ()
    assert lote.rejeitados == ()


def test_rejeita_linha_que_nao_e_objeto() -> None:
    lote = validar_lote(["ana"], CAMPOS_CLIENTES_RAW, chaves=("cliente_id",))  # type: ignore[list-item]
    assert lote.aceitos == ()
    assert lote.rejeitados[0].identificador == "linha-0"
    assert "objeto" in lote.rejeitados[0].motivo


def test_rejeita_coluna_ausente_nula_e_desconhecida() -> None:
    sem_nome = _cliente()
    del sem_nome["nome"]
    nula = _cliente(cliente_id="2", nome="   ")
    extra = _cliente(cliente_id="3")
    extra["apelido"] = "A"
    lote = validar_lote(
        [sem_nome, nula, extra],
        CAMPOS_CLIENTES_RAW,
        chaves=("cliente_id",),
    )
    assert lote.aceitos == ()
    motivos = [item.motivo for item in lote.rejeitados]
    assert any("ausentes" in motivo for motivo in motivos)
    assert any("nulo" in motivo for motivo in motivos)
    assert any("desconhecidas" in motivo for motivo in motivos)


def test_rejeita_chave_duplicada_e_mantem_a_primeira() -> None:
    lote = validar_lote(
        [_cliente(nome="Ana"), _cliente(nome="Outra")],
        CAMPOS_CLIENTES_RAW,
        chaves=("cliente_id",),
    )
    assert len(lote.aceitos) == 1
    assert lote.aceitos[0]["nome"] == "Ana"
    assert "duplicada" in lote.rejeitados[0].motivo


def test_rejeita_inteiro_invalido_bool_e_overflow() -> None:
    invalido = validar_lote(
        [_cliente(cliente_id="x")],
        CAMPOS_CLIENTES_RAW,
        chaves=("cliente_id",),
    )
    booleano = validar_lote(
        [_cliente() | {"cliente_id": True}],
        CAMPOS_CLIENTES_RAW,
        chaves=("cliente_id",),
    )
    enorme = validar_lote(
        [_cliente(cliente_id=str(2**63))],
        CAMPOS_CLIENTES_RAW,
        chaves=("cliente_id",),
    )
    assert "inteiro" in invalido.rejeitados[0].motivo
    assert "inteiro" in booleano.rejeitados[0].motivo
    assert "intervalo" in enorme.rejeitados[0].motivo


def test_rejeita_decimal_invalido_e_tipo_desconhecido() -> None:
    campo = Campo("valor", "decimal")
    with pytest.raises(ValueError, match="decimal"):
        coagir(campo, "abc")
    with pytest.raises(ValueError, match="decimal"):
        coagir(campo, float("inf"))
    with pytest.raises(ValueError, match="desconhecido"):
        coagir(Campo("quando", "data"), "hoje")


def test_valor_bruto_permanece_texto() -> None:
    pedido = {
        "pedido_id": "1",
        "cliente_id": "1",
        "livro": "Dom Casmurro",
        "valor": "42.90",
        "data_pedido": "2024-01-10",
    }
    lote = validar_lote([pedido], CAMPOS_PEDIDOS_RAW, chaves=("pedido_id",))
    assert lote.aceitos[0]["valor"] == "42.90"
    assert isinstance(lote.aceitos[0]["valor"], str)


def test_rejeita_pedido_sem_cliente_e_aceita_o_par() -> None:
    clientes = [_cliente(cliente_id="10"), _cliente(cliente_id="20", nome="Bruno")]
    clientes_ok = validar_lote(clientes, CAMPOS_CLIENTES_RAW, chaves=("cliente_id",))
    pedidos = [
        {
            "pedido_id": 1,
            "cliente_id": 10,
            "livro": "Dom",
            "valor": "10",
            "data_pedido": "2024-01-01",
        },
        {
            "pedido_id": 2,
            "cliente_id": 99,
            "livro": "Sumiu",
            "valor": "10",
            "data_pedido": "2024-01-02",
        },
    ]
    lote = rejeitar_pedidos_sem_cliente(pedidos, list(clientes_ok.aceitos))
    assert [linha["pedido_id"] for linha in lote.aceitos] == [1]
    assert lote.rejeitados[0].identificador == "2"
    assert lote.rejeitados[0].motivo == "Pedido sem cliente correspondente."


def test_rejeita_cliente_id_ausente_no_pedido() -> None:
    lote = rejeitar_pedidos_sem_cliente([{"pedido_id": 7}], [])
    assert lote.aceitos == ()
    assert lote.rejeitados[0].motivo == "cliente_id inválido."
