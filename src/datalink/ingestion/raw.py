"""Carga da camada raw a partir dos CSVs."""

from __future__ import annotations

from pathlib import Path

from datalink.domain.banco import Repositorio
from datalink.domain.contratos import (
    CAMPOS_CLIENTES_RAW,
    CAMPOS_PEDIDOS_RAW,
    Carga,
    colunas_api,
)
from datalink.infrastructure.publicacao import substituir_tabela
from datalink.ingestion.csv import ler_csv
from datalink.validation.camadas import validar_lote


def carregar_raw(banco: Repositorio, diretorio: Path) -> Carga:
    """Valida os CSVs e recria raw_clientes e raw_pedidos."""
    clientes_lidos = ler_csv(diretorio / "clientes.csv")
    pedidos_lidos = ler_csv(diretorio / "pedidos.csv")
    clientes = validar_lote(clientes_lidos, CAMPOS_CLIENTES_RAW, chaves=("cliente_id",))
    pedidos = validar_lote(pedidos_lidos, CAMPOS_PEDIDOS_RAW, chaves=("pedido_id",))
    substituir_tabela(
        banco,
        "raw_clientes",
        colunas_api(CAMPOS_CLIENTES_RAW),
        list(clientes.aceitos),
    )
    substituir_tabela(
        banco,
        "raw_pedidos",
        colunas_api(CAMPOS_PEDIDOS_RAW),
        list(pedidos.aceitos),
    )
    rejeitados = clientes.rejeitados + pedidos.rejeitados
    return Carga(
        volumes={
            "raw_clientes": len(clientes.aceitos),
            "raw_pedidos": len(pedidos.aceitos),
        },
        rejeitados=rejeitados,
        lidos=len(clientes_lidos) + len(pedidos_lidos),
        aceitos=len(clientes.aceitos) + len(pedidos.aceitos),
    )
