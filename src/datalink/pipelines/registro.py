"""Registro estruturado ao fim de cada etapa."""

from __future__ import annotations

import time

from datalink.domain.contratos import Carga
from datalink.utils.log import registrar_etapa, registrar_rejeicao


def registrar_carga(nome: str, carga: Carga, inicio: float) -> None:
    """Grava volumes, duração e cada rejeição da etapa."""
    registrar_etapa(
        nome,
        lido=carga.lidos,
        aceito=carga.aceitos,
        rejeitado=len(carga.rejeitados),
        duracao_s=time.perf_counter() - inicio,
    )
    for rejeicao in carga.rejeitados:
        registrar_rejeicao(nome, rejeicao.identificador, rejeicao.motivo)
