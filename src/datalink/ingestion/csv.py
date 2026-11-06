"""Leitura dos CSVs de origem."""

from __future__ import annotations

import csv
from pathlib import Path


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    """Lê o CSV e devolve as linhas como texto, sem transformar o negócio."""
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return [dict(linha) for linha in csv.DictReader(arquivo)]
