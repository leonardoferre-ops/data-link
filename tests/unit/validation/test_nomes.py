import pytest

from datalink.domain.erros import ErroConsulta
from datalink.validation.nomes import (
    citar,
    validar_nome,
    validar_nome_coluna,
    validar_select,
)


def test_select_simples_e_with_passam() -> None:
    assert validar_select("  SELECT 1  ") == "SELECT 1"
    assert validar_select("WITH t AS (SELECT 1) SELECT * FROM t").startswith("WITH")


def test_select_permite_sqlite_version_e_ignora_comentario() -> None:
    assert "sqlite_version" in validar_select("SELECT sqlite_version()")
    assert (
        validar_select("SELECT 1 -- drop table livros")
        == "SELECT 1 -- drop table livros"
    )
    assert validar_select("SELECT 'a;b' AS texto") == "SELECT 'a;b' AS texto"


def test_rejeita_sql_vazio_nao_texto_nulo_e_longo() -> None:
    with pytest.raises(ErroConsulta, match="SELECT"):
        validar_select("   ")
    with pytest.raises(ErroConsulta, match="texto"):
        validar_select(None)  # type: ignore[arg-type]
    with pytest.raises(ErroConsulta, match="caractere"):
        validar_select("SELECT '\x00'")
    with pytest.raises(ErroConsulta, match="5000"):
        validar_select("SELECT " + ("a" * 5000))


def test_rejeita_escrita_ponto_e_virgula_e_tabela_interna() -> None:
    with pytest.raises(ErroConsulta, match="SELECT"):
        validar_select("DROP TABLE livros")
    with pytest.raises(ErroConsulta, match="insert"):
        validar_select("WITH t AS (SELECT 1) INSERT INTO livros VALUES (1)")
    with pytest.raises(ErroConsulta, match="ponto e vírgula"):
        validar_select("SELECT 1; SELECT 2")
    with pytest.raises(ErroConsulta, match="internas"):
        validar_select("SELECT * FROM _banco_colunas")


def test_rejeita_comentario_e_aspas_sem_fechar_e_funcao_interna() -> None:
    with pytest.raises(ErroConsulta, match="Comentário"):
        validar_select("SELECT 1 /* sem fim")
    with pytest.raises(ErroConsulta, match="Aspas"):
        validar_select("SELECT 'sem fim")
    with pytest.raises(ErroConsulta, match="internas"):
        validar_select("SELECT sqlite_compileoption_get(0)")


def test_nome_valido_reservado_e_citacao() -> None:
    assert validar_nome("raw_clientes", o_que="Tabela") == "raw_clientes"
    with pytest.raises(ErroConsulta, match="inválido"):
        validar_nome("123", o_que="Tabela")
    with pytest.raises(ErroConsulta, match="sqlite_"):
        validar_nome("sqlite_segredo", o_que="Tabela")
    with pytest.raises(ErroConsulta, match="reservada"):
        validar_nome_coluna("id")
    assert citar("cidade") == '"cidade"'
