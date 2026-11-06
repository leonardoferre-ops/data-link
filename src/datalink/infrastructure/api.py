"""API HTTP do banco local."""

from __future__ import annotations

import sqlite3
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from datalink.config.ambiente import carregar_config
from datalink.domain.erros import ErroConsulta
from datalink.infrastructure.esquemas import (
    AtualizarIn,
    ConsultaIn,
    LinhasIn,
    SqlIn,
    TabelaIn,
)
from datalink.infrastructure.sqlite import (
    apagar_linha,
    apagar_tabela,
    atualizar_linha,
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

RESERVADOS = {"limite", "deslocamento", "ordenar", "direcao"}


@asynccontextmanager
async def vida(app: FastAPI) -> AsyncIterator[None]:
    """Abre o SQLite, prepara o catálogo e semeia livros quando permitido."""
    config = carregar_config()
    app.state.caminho = config.banco_caminho
    app.state.limite_sql_segundos = config.limite_sql_segundos
    conn = conectar(config.banco_caminho)
    try:
        preparar(conn)
        if config.semear_exemplo:
            semear(conn)
        conn.commit()
    finally:
        conn.close()
    yield


def criar_aplicacao() -> FastAPI:
    """Monta a API com as rotas do banco local."""
    app = FastAPI(
        title="Banco Local",
        summary="API gratuita para criar tabelas SQLite e consultar com Python.",
        version="1.0.0",
        description=(
            "O banco fica no arquivo `data/banco.db` desta máquina. "
            "Não há chave, conta nem cobrança. "
            "Crie tabelas, grave linhas e filtre em `/consulta` "
            "ou com SELECT somente leitura em `/sql`. "
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
    _registrar_erros(app)
    _incluir_rotas(app)
    return app


def obter_conn(request: Request) -> Iterator[sqlite3.Connection]:
    """Abre uma transação e desfaz o que a requisição não concluiu."""
    conn = conectar(request.app.state.caminho)
    try:
        yield conn
    except Exception:  # desfaz a transação e relança a falha da requisição
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        conn.close()


Conexao = Annotated[sqlite3.Connection, Depends(obter_conn)]


def _erro_consulta(_request: Request, exc: ErroConsulta) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": exc.mensagem})


def _erro_integridade(_request: Request, _exc: sqlite3.IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": "Os dados violam uma regra da tabela."},
    )


def _erro_sqlite(_request: Request, _exc: sqlite3.Error) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": "Não foi possível executar a operação no banco."},
    )


def _registrar_erros(app: FastAPI) -> None:
    """Traduz erros de domínio e do SQLite em respostas HTTP."""
    app.add_exception_handler(ErroConsulta, _erro_consulta)
    app.add_exception_handler(sqlite3.IntegrityError, _erro_integridade)
    app.add_exception_handler(sqlite3.Error, _erro_sqlite)


def inicio() -> dict[str, str]:
    """Lista os caminhos principais da API."""
    return {
        "nome": "Banco Local",
        "docs": "/docs",
        "saude": "/saude",
        "tabelas": "/tabelas",
        "consulta": "/consulta",
        "sql": "/sql",
    }


def saude() -> dict[str, str]:
    """Confere se a API e o SQLite estão disponíveis."""
    return {"status": "ok", "banco": "sqlite"}


def tabelas(conn: Conexao) -> list[dict[str, Any]]:
    """Lista as tabelas de usuário."""
    return listar_tabelas(conn)


def nova_tabela(corpo: TabelaIn, conn: Conexao) -> dict[str, Any]:
    """Cria uma tabela."""
    colunas = [coluna.model_dump() for coluna in corpo.colunas]
    return criar_tabela(conn, corpo.nome, colunas)


def ver_tabela(nome: str, conn: Conexao) -> dict[str, Any]:
    """Devolve o esquema da tabela."""
    return esquema(conn, nome)


def remover_tabela(nome: str, conn: Conexao) -> None:
    """Remove a tabela."""
    apagar_tabela(conn, nome)


def novas_linhas(nome: str, corpo: LinhasIn, conn: Conexao) -> dict[str, Any]:
    """Insere linhas na tabela."""
    return {"linhas": inserir_linhas(conn, nome, corpo.linhas)}


def linhas(
    nome: str,
    request: Request,
    conn: Conexao,
    limite: Annotated[int, Query(ge=1, le=500)] = 50,
    deslocamento: Annotated[int, Query(ge=0, le=100_000)] = 0,
    ordenar: str | None = None,
    direcao: Literal["asc", "desc"] = "asc",
) -> dict[str, Any]:
    """Lista linhas, tratando os demais query params como filtro de igualdade."""
    ordem = [{"coluna": ordenar, "direcao": direcao}] if ordenar else None
    return listar_linhas(
        conn,
        nome,
        filtros=_filtros_da_url(request),
        ordenar=ordem,
        limite=limite,
        deslocamento=deslocamento,
        filtros_texto=True,
    )


def uma_linha(nome: str, identificador: int, conn: Conexao) -> dict[str, Any]:
    """Obtém uma linha pelo id."""
    return obter_linha(conn, nome, identificador)


def editar_linha(
    nome: str,
    identificador: int,
    corpo: AtualizarIn,
    conn: Conexao,
) -> dict[str, Any]:
    """Atualiza colunas de uma linha."""
    return atualizar_linha(conn, nome, identificador, corpo.valores)


def remover_linha(nome: str, identificador: int, conn: Conexao) -> None:
    """Apaga uma linha pelo id."""
    apagar_linha(conn, nome, identificador)


def consulta(corpo: ConsultaIn, conn: Conexao) -> dict[str, Any]:
    """Filtra, ordena e projeta colunas sem SQL livre."""
    return listar_linhas(
        conn,
        corpo.tabela,
        filtros=[filtro.model_dump() for filtro in corpo.filtros],
        ordenar=[ordem.model_dump() for ordem in corpo.ordenar],
        colunas=corpo.colunas,
        limite=corpo.limite,
        deslocamento=corpo.deslocamento,
    )


def sql(corpo: SqlIn, request: Request) -> dict[str, Any]:
    """Executa um SELECT somente leitura."""
    return executar_select(
        request.app.state.caminho,
        corpo.sql,
        corpo.parametros,
        limite_s=request.app.state.limite_sql_segundos,
    )


def _incluir_rotas(app: FastAPI) -> None:
    """Registra as rotas da API."""
    app.add_api_route("/", inicio, methods=["GET"], tags=["Início"])
    app.add_api_route("/saude", saude, methods=["GET"], tags=["Início"])
    app.add_api_route("/tabelas", tabelas, methods=["GET"], tags=["Tabelas"])
    app.add_api_route(
        "/tabelas", nova_tabela, methods=["POST"], status_code=201, tags=["Tabelas"]
    )
    app.add_api_route("/tabelas/{nome}", ver_tabela, methods=["GET"], tags=["Tabelas"])
    app.add_api_route(
        "/tabelas/{nome}",
        remover_tabela,
        methods=["DELETE"],
        status_code=204,
        tags=["Tabelas"],
    )
    app.add_api_route(
        "/tabelas/{nome}/linhas",
        novas_linhas,
        methods=["POST"],
        status_code=201,
        tags=["Linhas"],
    )
    app.add_api_route(
        "/tabelas/{nome}/linhas", linhas, methods=["GET"], tags=["Linhas"]
    )
    app.add_api_route(
        "/tabelas/{nome}/linhas/{identificador}",
        uma_linha,
        methods=["GET"],
        tags=["Linhas"],
    )
    app.add_api_route(
        "/tabelas/{nome}/linhas/{identificador}",
        editar_linha,
        methods=["PATCH"],
        tags=["Linhas"],
    )
    app.add_api_route(
        "/tabelas/{nome}/linhas/{identificador}",
        remover_linha,
        methods=["DELETE"],
        status_code=204,
        tags=["Linhas"],
    )
    app.add_api_route("/consulta", consulta, methods=["POST"], tags=["Consultas"])
    app.add_api_route("/sql", sql, methods=["POST"], tags=["Consultas"])


def _filtros_da_url(request: Request) -> list[dict[str, str]]:
    filtros = []
    vistos: set[str] = set()
    for chave, valor in request.query_params.multi_items():
        if chave in RESERVADOS:
            continue
        if chave in vistos:
            raise ErroConsulta(400, f"Filtro repetido: {chave}.")
        vistos.add(chave)
        filtros.append({"coluna": chave, "op": "igual", "valor": valor})
    return filtros


app = criar_aplicacao()
