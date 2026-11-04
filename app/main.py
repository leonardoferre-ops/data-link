"""API HTTP do banco local."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from app.banco import (
    apagar_linha,
    apagar_tabela,
    atualizar_linha,
    caminho_padrao,
    conectar,
    criar_tabela,
    esquema,
    executar_select,
    inserir_linhas,
    listar_linhas,
    listar_tabelas,
    obter_linha,
    preparar,
    semear,
)
from app.erros import ErroConsulta
from app.esquemas import AtualizarIn, ConsultaIn, LinhasIn, SqlIn, TabelaIn

RESERVADOS = {"limite", "deslocamento", "ordenar", "direcao"}


@asynccontextmanager
async def vida(app: FastAPI):
    caminho = caminho_padrao()
    app.state.caminho = caminho
    conn = conectar(caminho)
    try:
        preparar(conn)
        if os.environ.get("BANCO_SEM_EXEMPLO") != "1":
            semear(conn)
        conn.commit()
    finally:
        conn.close()
    yield


def criar_aplicacao() -> FastAPI:
    app = FastAPI(
        title="Banco Local",
        summary="API gratuita para criar tabelas SQLite e consultar com Python.",
        version="1.0.0",
        description=(
            "O banco fica no arquivo `data/banco.db` desta máquina. "
            "Não há chave, conta nem cobrança. "
            "Crie tabelas, grave linhas e filtre em `/consulta` ou com SELECT somente leitura em `/sql`. "
            "A coleção `livros` já vem carregada para você experimentar."
        ),
        lifespan=vida,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def obter_conn(request: Request) -> Iterator[sqlite3.Connection]:
        conn = conectar(request.app.state.caminho)
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()

    def endpoint(fn):
        @wraps(fn)
        def interno(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except ErroConsulta as exc:
                raise HTTPException(status_code=exc.status, detail=exc.mensagem) from exc
            except sqlite3.IntegrityError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Os dados violam uma regra da tabela.",
                ) from exc
            except sqlite3.Error as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Não foi possível executar a operação no banco.",
                ) from exc

        return interno

    @app.get("/", tags=["Início"])
    def inicio() -> dict[str, str]:
        return {
            "nome": "Banco Local",
            "docs": "/docs",
            "saude": "/saude",
            "tabelas": "/tabelas",
            "consulta": "/consulta",
            "sql": "/sql",
        }

    @app.get("/saude", tags=["Início"])
    def saude() -> dict[str, str]:
        return {"status": "ok", "banco": "sqlite"}

    @app.get("/tabelas", tags=["Tabelas"])
    @endpoint
    def tabelas(conn: sqlite3.Connection = Depends(obter_conn)) -> list[dict[str, Any]]:
        return listar_tabelas(conn)

    @app.post("/tabelas", status_code=201, tags=["Tabelas"])
    @endpoint
    def nova_tabela(
        corpo: TabelaIn,
        conn: sqlite3.Connection = Depends(obter_conn),
    ) -> dict[str, Any]:
        return criar_tabela(
            conn,
            corpo.nome,
            [coluna.model_dump() for coluna in corpo.colunas],
        )

    @app.get("/tabelas/{nome}", tags=["Tabelas"])
    @endpoint
    def ver_tabela(
        nome: str,
        conn: sqlite3.Connection = Depends(obter_conn),
    ) -> dict[str, Any]:
        return esquema(conn, nome)

    @app.delete("/tabelas/{nome}", status_code=204, tags=["Tabelas"])
    @endpoint
    def remover_tabela(
        nome: str,
        conn: sqlite3.Connection = Depends(obter_conn),
    ) -> None:
        apagar_tabela(conn, nome)

    @app.post("/tabelas/{nome}/linhas", status_code=201, tags=["Linhas"])
    @endpoint
    def novas_linhas(
        nome: str,
        corpo: LinhasIn,
        conn: sqlite3.Connection = Depends(obter_conn),
    ) -> dict[str, Any]:
        return {"linhas": inserir_linhas(conn, nome, corpo.linhas)}

    @app.get("/tabelas/{nome}/linhas", tags=["Linhas"])
    @endpoint
    def linhas(
        nome: str,
        request: Request,
        conn: sqlite3.Connection = Depends(obter_conn),
        limite: int = Query(50, ge=1, le=500),
        deslocamento: int = Query(0, ge=0, le=100_000),
        ordenar: str | None = None,
        direcao: Literal["asc", "desc"] = "asc",
    ) -> dict[str, Any]:
        filtros = []
        vistos: set[str] = set()
        for chave, valor in request.query_params.multi_items():
            if chave in RESERVADOS:
                continue
            if chave in vistos:
                raise ErroConsulta(400, f"Filtro repetido: {chave}.")
            vistos.add(chave)
            filtros.append({"coluna": chave, "op": "igual", "valor": valor})
        ordem = [{"coluna": ordenar, "direcao": direcao}] if ordenar else None
        return listar_linhas(
            conn,
            nome,
            filtros=filtros,
            ordenar=ordem,
            limite=limite,
            deslocamento=deslocamento,
            filtros_texto=True,
        )

    @app.get("/tabelas/{nome}/linhas/{identificador}", tags=["Linhas"])
    @endpoint
    def uma_linha(
        nome: str,
        identificador: int,
        conn: sqlite3.Connection = Depends(obter_conn),
    ) -> dict[str, Any]:
        return obter_linha(conn, nome, identificador)

    @app.patch("/tabelas/{nome}/linhas/{identificador}", tags=["Linhas"])
    @endpoint
    def editar_linha(
        nome: str,
        identificador: int,
        corpo: AtualizarIn,
        conn: sqlite3.Connection = Depends(obter_conn),
    ) -> dict[str, Any]:
        return atualizar_linha(conn, nome, identificador, corpo.valores)

    @app.delete("/tabelas/{nome}/linhas/{identificador}", status_code=204, tags=["Linhas"])
    @endpoint
    def remover_linha(
        nome: str,
        identificador: int,
        conn: sqlite3.Connection = Depends(obter_conn),
    ) -> None:
        apagar_linha(conn, nome, identificador)

    @app.post("/consulta", tags=["Consultas"])
    @endpoint
    def consulta(
        corpo: ConsultaIn,
        conn: sqlite3.Connection = Depends(obter_conn),
    ) -> dict[str, Any]:
        return listar_linhas(
            conn,
            corpo.tabela,
            filtros=[filtro.model_dump() for filtro in corpo.filtros],
            ordenar=[ordem.model_dump() for ordem in corpo.ordenar],
            colunas=corpo.colunas,
            limite=corpo.limite,
            deslocamento=corpo.deslocamento,
        )

    @app.post("/sql", tags=["Consultas"])
    @endpoint
    def sql(corpo: SqlIn, request: Request) -> dict[str, Any]:
        return executar_select(request.app.state.caminho, corpo.sql, corpo.parametros)

    return app


app = criar_aplicacao()
