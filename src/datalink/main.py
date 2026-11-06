"""Ponto de entrada do pipeline Data Link."""

from datalink.config.ambiente import carregar_config
from datalink.pipelines.executar import executar


def main() -> None:
    """Carrega a configuração e dispara o pipeline completo."""
    executar(carregar_config())
