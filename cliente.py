"""Cliente Python da API Banco Local."""

from __future__ import annotations

import os
from typing import Any

import httpx


class ErroBanco(Exception):
    def __init__(self, status: int, detalhe: object) -> None:
        self.status = status
        self.detalhe = detalhe
        super().__init__(f"{status}: {detalhe}")


class Banco:
    """Fala com a API em `url` (padrão http://127.0.0.1:8741)."""

    def __init__(
        self,
        url: str | None = None,
        timeout: float = 10.0,
        cliente_http: httpx.Client | None = None,
    ) -> None:
        self.url = (url or os.environ.get("BANCO_URL") or "http://127.0.0.1:8741").rstrip("/")
        if cliente_http is None:
            self._cliente = httpx.Client(base_url=self.url, timeout=timeout)
            self._fechar = True
        else:
            self._cliente = cliente_http
            self._fechar = False

    def close(self) -> None:
        if self._fechar:
            self._cliente.close()

    def __enter__(self) -> Banco:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def saude(self) -> dict[str, Any]:
        return self._pedir("GET", "/saude")

    def tabelas(self) -> list[dict[str, Any]]:
        return self._pedir("GET", "/tabelas")

    def criar_tabela(self, nome: str, colunas: list[dict[str, Any]]) -> dict[str, Any]:
        return self._pedir("POST", "/tabelas", json={"nome": nome, "colunas": colunas})

    def apagar_tabela(self, nome: str) -> None:
        self._pedir("DELETE", f"/tabelas/{nome}")

    def esquema(self, nome: str) -> dict[str, Any]:
        return self._pedir("GET", f"/tabelas/{nome}")

    def inserir(self, tabela: str, linhas: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        pacote = linhas if isinstance(linhas, list) else [linhas]
        corpo = self._pedir("POST", f"/tabelas/{tabela}/linhas", json={"linhas": pacote})
        return corpo["linhas"]

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
        params: dict[str, Any] = {"limite": limite, "deslocamento": deslocamento, "direcao": direcao}
        if ordenar:
            params["ordenar"] = ordenar
        for coluna, valor in iguais.items():
            if isinstance(valor, bool):
                params[coluna] = "true" if valor else "false"
            elif valor is None:
                params[coluna] = "null"
            else:
                params[coluna] = valor
        return self._pedir("GET", f"/tabelas/{tabela}/linhas", params=params)

    def obter(self, tabela: str, identificador: int) -> dict[str, Any]:
        return self._pedir("GET", f"/tabelas/{tabela}/linhas/{identificador}")

    def atualizar(self, tabela: str, identificador: int, valores: dict[str, Any]) -> dict[str, Any]:
        return self._pedir(
            "PATCH",
            f"/tabelas/{tabela}/linhas/{identificador}",
            json={"valores": valores},
        )

    def apagar(self, tabela: str, identificador: int) -> None:
        self._pedir("DELETE", f"/tabelas/{tabela}/linhas/{identificador}")

    def consultar(
        self,
        tabela: str,
        *,
        colunas: list[str] | None = None,
        filtros: list[dict[str, Any]] | None = None,
        ordenar: list[dict[str, str]] | None = None,
        limite: int = 50,
        deslocamento: int = 0,
    ) -> dict[str, Any]:
        corpo: dict[str, Any] = {
            "tabela": tabela,
            "filtros": filtros or [],
            "ordenar": ordenar or [],
            "limite": limite,
            "deslocamento": deslocamento,
        }
        if colunas is not None:
            corpo["colunas"] = colunas
        return self._pedir("POST", "/consulta", json=corpo)

    def sql(self, consulta: str, parametros: list[Any] | None = None) -> dict[str, Any]:
        return self._pedir("POST", "/sql", json={"sql": consulta, "parametros": parametros or []})

    def _pedir(self, metodo: str, caminho: str, *, json: Any = None, params: dict[str, Any] | None = None) -> Any:
        try:
            resposta = self._cliente.request(metodo, caminho, json=json, params=params)
        except httpx.ConnectError as exc:
            raise ErroBanco(
                0,
                f"Não conectou em {self.url}. Suba a API com: uvicorn app.main:app --host 127.0.0.1 --port 8741",
            ) from exc
        if resposta.status_code >= 400:
            detalhe: object = resposta.text
            tipo = resposta.headers.get("content-type", "")
            if tipo.startswith("application/json"):
                corpo = resposta.json()
                detalhe = corpo.get("detail", corpo)
            raise ErroBanco(resposta.status_code, detalhe)
        if resposta.status_code == 204 or not resposta.content:
            return None
        return resposta.json()
