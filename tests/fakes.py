"""Banco em memória para os testes do pipeline."""

from __future__ import annotations

from typing import Any

from datalink.infrastructure.cliente import ErroBanco


class BancoMemoria:
    """Implementa o protocolo do repositório sem arquivo e sem rede."""

    def __init__(self) -> None:
        self.tabelas: dict[str, dict[str, Any]] = {}

    def apagar_tabela(self, nome: str) -> None:
        if nome not in self.tabelas:
            raise ErroBanco(404, f"Tabela {nome} não encontrada.")
        del self.tabelas[nome]

    def criar_tabela(self, nome: str, colunas: list[dict[str, Any]]) -> dict[str, Any]:
        if nome in self.tabelas:
            raise ErroBanco(409, f"A tabela {nome} já existe.")
        self.tabelas[nome] = {"colunas": colunas, "linhas": []}
        return {"nome": nome, "colunas": colunas}

    def inserir(
        self,
        tabela: str,
        linhas: dict[str, Any] | list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        pacote = linhas if isinstance(linhas, list) else [linhas]
        copias = [dict(linha) for linha in pacote]
        self.tabelas[tabela]["linhas"].extend(copias)
        return copias

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
        if tabela not in self.tabelas:
            raise ErroBanco(404, f"Tabela {tabela} não encontrada.")
        linhas = [dict(linha) for linha in self.tabelas[tabela]["linhas"]]
        for coluna, valor in iguais.items():
            linhas = [linha for linha in linhas if linha.get(coluna) == valor]
        if ordenar:
            linhas.sort(key=lambda linha: linha.get(ordenar), reverse=direcao == "desc")
        total = len(linhas)
        recorte = linhas[deslocamento : deslocamento + limite]
        return {
            "tabela": tabela,
            "total": total,
            "limite": limite,
            "deslocamento": deslocamento,
            "linhas": recorte,
        }
