"""Publicação idempotente de uma tabela inteira."""

from __future__ import annotations

from typing import Any

from datalink.config.limites import LOTE_GRAVACAO
from datalink.domain.banco import Repositorio
from datalink.infrastructure.cliente import ErroBanco

STATUS_AUSENTE = 404
STATUS_CONFLITO = 409


def substituir_tabela(
    banco: Repositorio,
    nome: str,
    colunas: list[dict[str, Any]],
    linhas: list[dict[str, Any]],
) -> None:
    """Apaga a tabela, cria de novo e grava só as linhas aceitas."""
    _remover(banco, nome)
    _criar(banco, nome, colunas)
    _gravar(banco, nome, linhas)


def _remover(banco: Repositorio, nome: str) -> None:
    try:
        banco.apagar_tabela(nome)
    except ErroBanco as exc:
        if exc.status != STATUS_AUSENTE:
            raise


def _criar(banco: Repositorio, nome: str, colunas: list[dict[str, Any]]) -> None:
    try:
        banco.criar_tabela(nome, colunas)
    except ErroBanco as exc:
        if exc.status != STATUS_CONFLITO:
            raise
        _remover(banco, nome)
        banco.criar_tabela(nome, colunas)


def _gravar(banco: Repositorio, nome: str, linhas: list[dict[str, Any]]) -> None:
    for inicio in range(0, len(linhas), LOTE_GRAVACAO):
        banco.inserir(nome, linhas[inicio : inicio + LOTE_GRAVACAO])
