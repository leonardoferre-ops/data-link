"""Registra alterações do projeto em logs/alteracoes.log."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DIR_LOGS = Path(__file__).resolve().parent
ARQUIVO = DIR_LOGS / "alteracoes.log"
TIPOS = ("ADD", "CHG", "FIX", "DEL", "DOCS", "TEST", "INIT")


def registrar(tipo: str, mensagem: str) -> Path:
    """Acrescenta uma linha de log com data/hora local."""
    tipo_ok = tipo.upper().strip()
    if tipo_ok not in TIPOS:
        raise ValueError(f"Tipo inválido: {tipo}. Use um de: {', '.join(TIPOS)}")

    agora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M")
    linha = f"[{agora}] {tipo_ok:<4} | {mensagem.strip()}\n"
    DIR_LOGS.mkdir(parents=True, exist_ok=True)
    with ARQUIVO.open("a", encoding="utf-8") as arquivo:
        arquivo.write(linha)
    return ARQUIVO


def main() -> None:
    parser = argparse.ArgumentParser(description="Grava log de alteração do projeto.")
    parser.add_argument(
        "tipo",
        choices=TIPOS,
        help="Tipo da alteração (ADD, CHG, FIX, DEL, DOCS, TEST, INIT)",
    )
    parser.add_argument("mensagem", help="Descrição do que mudou")
    args = parser.parse_args()
    caminho = registrar(args.tipo, args.mensagem)
    print(f"Registrado em {caminho}")


if __name__ == "__main__":
    main()
