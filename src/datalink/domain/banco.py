"""Protocolo do repositório usado pelo pipeline."""

from __future__ import annotations

from typing import Any, Protocol


class Repositorio(Protocol):
    """Contrato do banco usado pelo pipeline, sem amarrar o driver."""

    def apagar_tabela(self, nome: str) -> None:
        """Remove a tabela."""

    def criar_tabela(self, nome: str, colunas: list[dict[str, Any]]) -> dict[str, Any]:
        """Cria a tabela com as colunas informadas."""

    def inserir(
        self,
        tabela: str,
        linhas: dict[str, Any] | list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Inclui uma ou mais linhas e devolve as linhas gravadas."""

    def listar(
        self,
        tabela: str,
        *,
        limite: int = 50,
        deslocamento: int = 0,
        ordenar: str | None = None,
        direcao: str = "asc",
        **iguais: Any,
    ) -> dict[str, Any]:
        """Lista linhas da tabela."""
