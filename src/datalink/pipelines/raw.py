"""Etapa raw: CSV validado para as tabelas raw."""

from __future__ import annotations

import time
from pathlib import Path

from datalink.config.ambiente import Configuracao
from datalink.domain.banco import Repositorio
from datalink.domain.contratos import Carga
from datalink.ingestion.raw import carregar_raw
from datalink.pipelines.cli import disparar
from datalink.pipelines.registro import registrar_carga


def publicar_raw(banco: Repositorio, diretorio: Path) -> Carga:
    """Carrega a camada raw e registra volumes e rejeições."""
    inicio = time.perf_counter()
    carga = carregar_raw(banco, diretorio)
    registrar_carga("raw", carga, inicio)
    return carga


def _subir(banco: Repositorio, config: Configuracao) -> Carga:
    return publicar_raw(banco, config.diretorio_bruto)


def main() -> None:
    """Carrega somente a camada raw."""
    disparar(_subir)


if __name__ == "__main__":
    main()
