from pathlib import Path

import pytest
from tests.fakes import BancoMemoria

from datalink.domain.contratos import Carga
from datalink.infrastructure.cliente import ErroBanco
from datalink.infrastructure.publicacao import substituir_tabela
from datalink.pipelines.marts import publicar_marts
from datalink.pipelines.raw import publicar_raw
from datalink.pipelines.refined import publicar_refined


def _escrever(diretorio: Path) -> None:
    (diretorio / "clientes.csv").write_text(
        "cliente_id,nome,cidade,estado\n"
        "10, Ana , Recife ,pe\n"
        "20,Bruno,Salvador,BA\n"
        "10,Outra,Olinda,PE\n",
        encoding="utf-8",
    )
    (diretorio / "pedidos.csv").write_text(
        "pedido_id,cliente_id,livro,valor,data_pedido\n"
        "1,10, Dom Casmurro ,42.90,2024-01-10\n"
        "2,99,Inexistente,10.00,2024-01-11\n"
        "3,20,Vidas Secas,33.00,2024-02-01\n"
        "2,20,Duplicado,1.00,2024-02-02\n",
        encoding="utf-8",
    )


def test_pipeline_nao_abre_banco_do_projeto(
    tmp_path: Path, banco: BancoMemoria
) -> None:
    _escrever(tmp_path)
    bruto = publicar_raw(banco, tmp_path)
    refinado = publicar_refined(banco)
    indicadores = publicar_marts(banco)

    ana = next(
        linha
        for linha in banco.tabelas["raw_clientes"]["linhas"]
        if linha["cliente_id"] == 10
    )
    assert ana["nome"] == " Ana "
    assert ana["estado"] == "pe"
    pedido_bruto = next(
        linha
        for linha in banco.tabelas["raw_pedidos"]["linhas"]
        if linha["pedido_id"] == 1
    )
    assert pedido_bruto["valor"] == "42.90"
    assert bruto.volumes == {"raw_clientes": 2, "raw_pedidos": 3}
    assert any("duplicada" in item.motivo for item in bruto.rejeitados)

    refinado_um = next(
        linha
        for linha in banco.tabelas["refined_pedidos"]["linhas"]
        if linha["pedido_id"] == 1
    )
    assert refinado_um["cliente_nome"] == "Ana"
    assert refinado_um["estado"] == "PE"
    assert refinado_um["livro"] == "Dom Casmurro"
    assert refinado_um["valor"] == 42.90
    assert refinado.volumes == {"refined_pedidos": 2}
    assert any(
        item.motivo == "Pedido sem cliente correspondente."
        for item in refinado.rejeitados
    )

    resumo = {
        linha["indicador"]: linha["valor"]
        for linha in banco.tabelas["marts_resumo"]["linhas"]
    }
    assert resumo["qtd_pedidos"] == 2.0
    assert resumo["qtd_clientes"] == 2.0
    assert resumo["receita_total"] == 75.9
    assert resumo["ticket_medio"] == 37.95
    assert indicadores.volumes["marts_resumo"] == 4
    assert indicadores.volumes["marts_livros_cliente"] == 2
    assert not (tmp_path / "banco.db").exists()


def test_segunda_carga_substitui_sem_duplicar(
    tmp_path: Path, banco: BancoMemoria
) -> None:
    _escrever(tmp_path)
    publicar_raw(banco, tmp_path)
    publicar_refined(banco)
    publicar_marts(banco)
    primeira = [dict(linha) for linha in banco.tabelas["refined_pedidos"]["linhas"]]
    publicar_raw(banco, tmp_path)
    publicar_refined(banco)
    publicar_marts(banco)
    assert banco.tabelas["refined_pedidos"]["linhas"] == primeira
    assert len(banco.tabelas["marts_resumo"]["linhas"]) == 4


def test_valor_invalido_fica_na_raw_e_sai_da_refined(
    tmp_path: Path, banco: BancoMemoria
) -> None:
    (tmp_path / "clientes.csv").write_text(
        "cliente_id,nome,cidade,estado\n1,Ana,Recife,PE\n",
        encoding="utf-8",
    )
    (tmp_path / "pedidos.csv").write_text(
        "pedido_id,cliente_id,livro,valor,data_pedido\n"
        "1,1,Dom,abc,2024-01-01\n"
        "2,1,Vidas,10.00,2024-01-02\n",
        encoding="utf-8",
    )
    publicar_raw(banco, tmp_path)
    refinado = publicar_refined(banco)
    assert [linha["pedido_id"] for linha in banco.tabelas["raw_pedidos"]["linhas"]] == [
        1,
        2,
    ]
    assert [
        linha["pedido_id"] for linha in banco.tabelas["refined_pedidos"]["linhas"]
    ] == [2]
    assert any("Valor inválido" in item.motivo for item in refinado.rejeitados)


def test_csv_ausente_levanta_arquivo(tmp_path: Path, banco: BancoMemoria) -> None:
    with pytest.raises(FileNotFoundError):
        publicar_raw(banco, tmp_path)


def test_substituir_recria_e_lote_vazio(banco: BancoMemoria) -> None:
    colunas = [{"nome": "nome", "tipo": "texto", "obrigatorio": True}]
    substituir_tabela(banco, "contatos", colunas, [{"nome": "Ana"}])
    substituir_tabela(banco, "contatos", colunas, [])
    assert banco.tabelas["contatos"]["linhas"] == []


def test_substituir_propaga_falha_que_nao_e_ausencia() -> None:
    class BancoFalha(BancoMemoria):
        def apagar_tabela(self, _nome: str) -> None:
            raise ErroBanco(500, "falha")

    with pytest.raises(ErroBanco) as exc:
        substituir_tabela(BancoFalha(), "t", [{"nome": "a", "tipo": "texto"}], [])
    assert exc.value.status == 500


def test_substituir_trata_conflito_ao_criar() -> None:
    class BancoConflito(BancoMemoria):
        def __init__(self) -> None:
            super().__init__()
            self.forcar = True

        def criar_tabela(self, nome: str, colunas: list[dict]) -> dict:
            if self.forcar:
                self.forcar = False
                raise ErroBanco(409, "existe")
            return super().criar_tabela(nome, colunas)

    memoria = BancoConflito()
    substituir_tabela(memoria, "t", [{"nome": "a", "tipo": "texto"}], [{"a": "1"}])
    assert memoria.tabelas["t"]["linhas"] == [{"a": "1"}]


def test_carga_expoe_contagens(tmp_path: Path, banco: BancoMemoria) -> None:
    _escrever(tmp_path)
    carga = publicar_raw(banco, tmp_path)
    assert isinstance(carga, Carga)
    assert carga.lidos == 7
    assert carga.aceitos == 5
