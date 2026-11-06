"""Fachada da persistência SQLite."""

from datalink.infrastructure.sqlite_consulta import executar_select, listar_linhas
from datalink.infrastructure.sqlite_dados import (
    apagar_linha,
    atualizar_linha,
    inserir_linhas,
    obter_linha,
    semear,
)
from datalink.infrastructure.sqlite_meta import (
    apagar_tabela,
    conectar,
    criar_tabela,
    esquema,
    listar_tabelas,
    preparar,
)

__all__ = [
    "apagar_linha",
    "apagar_tabela",
    "atualizar_linha",
    "conectar",
    "criar_tabela",
    "esquema",
    "executar_select",
    "inserir_linhas",
    "listar_linhas",
    "listar_tabelas",
    "obter_linha",
    "preparar",
    "semear",
]
