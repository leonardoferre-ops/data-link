"""Etapa marts: indicadores materializados para o painel."""

from __future__ import annotations

import time
from typing import Any

from datalink.config.ambiente import Configuracao
from datalink.config.limites import LOTE_LEITURA
from datalink.domain.banco import Repositorio
from datalink.domain.contratos import (
    CAMPOS_MARTS,
    CAMPOS_PEDIDOS_REFINED,
    Carga,
    colunas_api,
)
from datalink.infrastructure.publicacao import substituir_tabela
from datalink.pipelines.cli import disparar
from datalink.pipelines.registro import registrar_carga
from datalink.transformations.marts import (
    livros_por_cliente,
    pedidos_por_cliente,
    resumo_indicadores,
    vendas_por_cidade,
)
from datalink.validation.camadas import sem_envelope, validar_lote

_CHAVES: dict[str, tuple[str, ...]] = {
    "marts_resumo": ("indicador",),
    "marts_vendas_cidade": ("cidade", "estado"),
    "marts_pedidos_cliente": ("cliente_id",),
    "marts_livros_cliente": ("pedido_id",),
}


def publicar_marts(banco: Repositorio) -> Carga:
    """Lê refined_pedidos e recria as quatro tabelas de indicadores."""
    inicio = time.perf_counter()
    lidos = _ler(banco)
    validos = validar_lote(lidos, CAMPOS_PEDIDOS_REFINED, chaves=("pedido_id",))
    produzidos = _produzir(list(validos.aceitos))
    volumes, rejeitados = _publicar(banco, produzidos)
    rejeitados = validos.rejeitados + tuple(rejeitados)
    carga = Carga(
        volumes=volumes,
        rejeitados=rejeitados,
        lidos=len(lidos),
        aceitos=len(validos.aceitos),
    )
    registrar_carga("marts", carga, inicio)
    return carga


def _ler(banco: Repositorio) -> list[dict[str, Any]]:
    linhas = banco.listar("refined_pedidos", limite=LOTE_LEITURA)["linhas"]
    return [sem_envelope(linha) for linha in linhas]


def _produzir(pedidos: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "marts_resumo": resumo_indicadores(pedidos),
        "marts_vendas_cidade": vendas_por_cidade(pedidos),
        "marts_pedidos_cliente": pedidos_por_cliente(pedidos),
        "marts_livros_cliente": livros_por_cliente(pedidos),
    }


def _publicar(
    banco: Repositorio,
    produzidos: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, int], list[Any]]:
    volumes: dict[str, int] = {}
    rejeitados: list[Any] = []
    for nome, linhas in produzidos.items():
        lote = validar_lote(linhas, CAMPOS_MARTS[nome], chaves=_CHAVES[nome])
        substituir_tabela(
            banco, nome, colunas_api(CAMPOS_MARTS[nome]), list(lote.aceitos)
        )
        volumes[nome] = len(lote.aceitos)
        rejeitados.extend(lote.rejeitados)
    return volumes, rejeitados


def _subir(banco: Repositorio, _config: Configuracao) -> Carga:
    return publicar_marts(banco)


def main() -> None:
    """Carrega somente a camada marts."""
    disparar(_subir)


if __name__ == "__main__":
    main()
