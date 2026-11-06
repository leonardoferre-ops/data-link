"""Orquestra raw, refined e marts."""

from __future__ import annotations

from datalink.config.ambiente import Configuracao
from datalink.domain.banco import Repositorio
from datalink.infrastructure.cliente import Banco, ErroBanco
from datalink.pipelines.marts import publicar_marts
from datalink.pipelines.raw import publicar_raw
from datalink.pipelines.refined import publicar_refined
from datalink.utils.log import configurar_log


def rodar(config: Configuracao, banco: Repositorio | None = None) -> None:
    """Executa raw, refined e marts, nesta ordem."""
    if banco is not None:
        _etapas(banco, config)
        return
    with Banco(config.banco_url) as cliente:
        _etapas(cliente, config)


def executar(config: Configuracao) -> None:
    """Dispara o pipeline e encerra o processo se a API estiver fora."""
    configurar_log()
    try:
        rodar(config)
    except ErroBanco as exc:
        raise SystemExit(str(exc)) from exc


def _etapas(banco: Repositorio, config: Configuracao) -> None:
    publicar_raw(banco, config.diretorio_bruto)
    publicar_refined(banco)
    publicar_marts(banco)
