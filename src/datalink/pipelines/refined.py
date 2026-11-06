"""Etapa refined: validação, JOIN e tipagem."""

from __future__ import annotations

import time
from typing import Any

from datalink.config.ambiente import Configuracao
from datalink.config.limites import LOTE_LEITURA
from datalink.domain.banco import Repositorio
from datalink.domain.contratos import (
    CAMPOS_CLIENTES_RAW,
    CAMPOS_PEDIDOS_RAW,
    CAMPOS_PEDIDOS_REFINED,
    Carga,
    Rejeicao,
    colunas_api,
)
from datalink.infrastructure.publicacao import substituir_tabela
from datalink.pipelines.cli import disparar
from datalink.pipelines.registro import registrar_carga
from datalink.transformations.refined import conformar_pedido
from datalink.validation.camadas import (
    rejeitar_pedidos_sem_cliente,
    sem_envelope,
    validar_lote,
)


def publicar_refined(banco: Repositorio) -> Carga:
    """Lê a raw, rejeita pedido sem cliente e recria refined_pedidos."""
    inicio = time.perf_counter()
    clientes = _ler(banco, "raw_clientes")
    pedidos = _ler(banco, "raw_pedidos")
    clientes_ok = validar_lote(clientes, CAMPOS_CLIENTES_RAW, chaves=("cliente_id",))
    pedidos_ok = validar_lote(pedidos, CAMPOS_PEDIDOS_RAW, chaves=("pedido_id",))
    com_cliente = rejeitar_pedidos_sem_cliente(
        list(pedidos_ok.aceitos),
        list(clientes_ok.aceitos),
    )
    conformados, falhas = _conformar(com_cliente.aceitos, clientes_ok.aceitos)
    finais = validar_lote(conformados, CAMPOS_PEDIDOS_REFINED, chaves=("pedido_id",))
    substituir_tabela(
        banco,
        "refined_pedidos",
        colunas_api(CAMPOS_PEDIDOS_REFINED),
        list(finais.aceitos),
    )
    rejeitados = (
        clientes_ok.rejeitados
        + pedidos_ok.rejeitados
        + com_cliente.rejeitados
        + falhas
        + finais.rejeitados
    )
    carga = Carga(
        volumes={"refined_pedidos": len(finais.aceitos)},
        rejeitados=rejeitados,
        lidos=len(pedidos),
        aceitos=len(finais.aceitos),
    )
    registrar_carga("refined", carga, inicio)
    return carga


def _ler(banco: Repositorio, tabela: str) -> list[dict[str, Any]]:
    linhas = banco.listar(tabela, limite=LOTE_LEITURA)["linhas"]
    return [sem_envelope(linha) for linha in linhas]


def _conformar(
    pedidos: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    clientes: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], tuple[Rejeicao, ...]]:
    indice = {int(cliente["cliente_id"]): cliente for cliente in clientes}
    aceitos: list[dict[str, Any]] = []
    rejeitados: list[Rejeicao] = []
    for pedido in pedidos:
        try:
            aceitos.append(conformar_pedido(pedido, indice[int(pedido["cliente_id"])]))
        except (KeyError, TypeError, ValueError) as exc:
            rejeitados.append(Rejeicao(str(pedido.get("pedido_id", "?")), str(exc)))
    return aceitos, tuple(rejeitados)


def _subir(banco: Repositorio, _config: Configuracao) -> Carga:
    return publicar_refined(banco)


def main() -> None:
    """Carrega somente a camada refined."""
    disparar(_subir)


if __name__ == "__main__":
    main()
