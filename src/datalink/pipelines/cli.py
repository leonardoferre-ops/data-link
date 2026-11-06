"""Disparo das etapas pela linha de comando."""

from __future__ import annotations

from collections.abc import Callable

from datalink.config.ambiente import Configuracao, carregar_config
from datalink.domain.banco import Repositorio
from datalink.domain.contratos import Carga
from datalink.infrastructure.cliente import Banco, ErroBanco
from datalink.utils.log import configurar_log


def disparar(acao: Callable[[Repositorio, Configuracao], Carga]) -> None:
    """Sobe o log, abre o cliente HTTP e converte falha de conexão em saída."""
    configurar_log()
    config = carregar_config()
    try:
        with Banco(config.banco_url) as banco:
            acao(banco, config)
    except ErroBanco as exc:
        raise SystemExit(str(exc)) from exc
