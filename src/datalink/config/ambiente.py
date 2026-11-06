"""Leitura de BANCO_URL, BANCO_CAMINHO e BANCO_SEM_EXEMPLO."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PORTA_API = 8741
URL_PADRAO = f"http://127.0.0.1:{PORTA_API}"
CAMINHO_PADRAO = "data/banco.db"


@dataclass(frozen=True)
class Configuracao:
    """Parâmetros de uma execução, lidos do ambiente."""

    banco_url: str
    banco_caminho: Path
    semear_exemplo: bool
    limite_sql_segundos: float
    diretorio_bruto: Path


def url_da_api() -> str:
    """Lê BANCO_URL ou devolve o endereço local da porta 8741."""
    bruto = os.environ.get("BANCO_URL") or URL_PADRAO
    return bruto.rstrip("/")


def caminho_do_banco() -> Path:
    """Lê BANCO_CAMINHO, cria o diretório pai e devolve o caminho absoluto."""
    bruto = os.environ.get("BANCO_CAMINHO", CAMINHO_PADRAO)
    caminho = Path(bruto).expanduser().resolve()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return caminho


def deve_semear_exemplo() -> bool:
    """Indica se a coleção livros deve ser semeada na subida da API."""
    return os.environ.get("BANCO_SEM_EXEMPLO") != "1"


def limite_sql_segundos() -> float:
    """Lê BANCO_SQL_SEGUNDOS. O padrão é 2 segundos."""
    return float(os.environ.get("BANCO_SQL_SEGUNDOS", "2"))


def diretorio_bruto() -> Path:
    """Pasta dos CSVs de origem, relativa ao diretório de trabalho."""
    return (Path.cwd() / "dados" / "bruto").resolve()


def carregar_config() -> Configuracao:
    """Monta a configuração atual do ambiente."""
    return Configuracao(
        banco_url=url_da_api(),
        banco_caminho=caminho_do_banco(),
        semear_exemplo=deve_semear_exemplo(),
        limite_sql_segundos=limite_sql_segundos(),
        diretorio_bruto=diretorio_bruto(),
    )
