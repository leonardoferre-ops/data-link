"""Utilitários compartilhados do pipeline."""

from __future__ import annotations

from typing import Any

from cliente import Banco, ErroBanco


def recriar_tabela(banco: Banco, nome: str, colunas: list[dict[str, Any]]) -> None:
    """Apaga (se existir) e cria a tabela de novo."""
    try:
        banco.apagar_tabela(nome)
    except ErroBanco:
        pass
    try:
        banco.criar_tabela(nome, colunas)
    except ErroBanco as exc:
        if exc.status != 409:
            raise
        try:
            banco.apagar_tabela(nome)
        except ErroBanco:
            pass
        banco.criar_tabela(nome, colunas)
