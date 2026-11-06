"""Log estruturado das etapas do pipeline."""

from __future__ import annotations

import logging

logger = logging.getLogger("datalink.pipeline")
logger.addHandler(logging.NullHandler())

_CAMPOS = (
    "pipeline",
    "volume_lido",
    "volume_aceito",
    "volume_rejeitado",
    "duracao_s",
    "identificador",
    "motivo",
)


class _FormatoEtapa(logging.Formatter):
    """Anexa os campos estruturados que a etapa tiver gravado."""

    def format(self, record: logging.LogRecord) -> str:
        """Devolve a mensagem e os extras presentes no registro."""
        base = super().format(record)
        extras = [
            f"{campo}={getattr(record, campo)}"
            for campo in _CAMPOS
            if hasattr(record, campo)
        ]
        if not extras:
            return base
        return base + " " + " ".join(extras)


def configurar_log() -> None:
    """Envia o log do pipeline para a saída padrão, uma vez por processo."""
    raiz = logging.getLogger()
    if raiz.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(_FormatoEtapa("%(levelname)s %(message)s"))
    raiz.addHandler(handler)
    raiz.setLevel(logging.INFO)


def registrar_etapa(
    nome: str,
    *,
    lido: int,
    aceito: int,
    rejeitado: int,
    duracao_s: float,
) -> None:
    """Registra volumes e duração de uma etapa."""
    logger.info(
        "etapa_concluida",
        extra={
            "pipeline": nome,
            "volume_lido": lido,
            "volume_aceito": aceito,
            "volume_rejeitado": rejeitado,
            "duracao_s": round(duracao_s, 6),
        },
    )


def registrar_rejeicao(nome: str, identificador: str, motivo: str) -> None:
    """Registra um registro rejeitado com identificador e motivo."""
    logger.warning(
        "registro_rejeitado",
        extra={
            "pipeline": nome,
            "identificador": identificador,
            "motivo": motivo,
        },
    )
