"""Inclusão, alteração, remoção e semeadura de linhas."""

from __future__ import annotations

import sqlite3
from typing import Any

from datalink.domain.erros import ErroConsulta
from datalink.infrastructure.sqlite_meta import (
    criar_tabela,
    executar_sql,
    exigir_tabela,
    sql_citado,
    tipos_completos,
    tipos_usuario,
)
from datalink.infrastructure.sqlite_valores import conferir_linha, serializar
from datalink.validation.nomes import citar

LIMITE_ENVIO = 200

LIVROS = [
    ("Dom Casmurro", "Machado de Assis", 1899, "romance", 42.90),
    ("Memórias Póstumas de Brás Cubas", "Machado de Assis", 1881, "romance", 38.50),
    ("O Cortiço", "Aluísio Azevedo", 1890, "romance", 35.00),
    ("Grande Sertão: Veredas", "Guimarães Rosa", 1956, "romance", 67.90),
    ("Vidas Secas", "Graciliano Ramos", 1938, "romance", 33.00),
    ("Capitães da Areia", "Jorge Amado", 1937, "romance", 39.90),
    ("Gabriela, Cravo e Canela", "Jorge Amado", 1958, "romance", 44.00),
    ("A Hora da Estrela", "Clarice Lispector", 1977, "novela", 36.50),
    ("O Avesso da Pele", "Jeferson Tenório", 2020, "romance", 54.90),
    ("Torto Arado", "Itamar Vieira Junior", 2019, "romance", 59.90),
    ("O Quinze", "Rachel de Queiroz", 1930, "romance", 32.00),
    ("Macunaíma", "Mário de Andrade", 1928, "romance", 41.00),
]


def semear(conn: sqlite3.Connection) -> None:
    """Cria a coleção livros quando ela ainda não existe."""
    existe = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'livros'"
    ).fetchone()
    if existe:
        return
    criar_tabela(
        conn,
        "livros",
        [
            {"nome": "titulo", "tipo": "texto", "obrigatorio": True},
            {"nome": "autor", "tipo": "texto", "obrigatorio": True},
            {"nome": "ano", "tipo": "inteiro", "obrigatorio": True},
            {"nome": "genero", "tipo": "texto", "obrigatorio": True},
            {"nome": "preco", "tipo": "decimal", "obrigatorio": True},
        ],
    )
    inserir_linhas(conn, "livros", [_livro(*item) for item in LIVROS])


def inserir_linhas(
    conn: sqlite3.Connection,
    tabela: str,
    linhas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Insere até 200 linhas e devolve cada uma como foi gravada."""
    exigir_tabela(conn, tabela)
    if not linhas:
        raise ErroConsulta(400, "Informe ao menos uma linha.")
    if len(linhas) > LIMITE_ENVIO:
        raise ErroConsulta(400, "O máximo por envio é 200 linhas.")
    tipos = tipos_usuario(conn, tabela)
    ids = [
        _inserir(conn, tabela, conferir_linha(tipos, linha, parcial=False))
        for linha in linhas
    ]
    return [obter_linha(conn, tabela, identificador) for identificador in ids]


def obter_linha(
    conn: sqlite3.Connection, tabela: str, identificador: int
) -> dict[str, Any]:
    """Devolve uma linha pelo id, ou 404 se ela não existir."""
    exigir_tabela(conn, tabela)
    tipos = tipos_completos(conn, tabela)
    row = executar_sql(
        conn,
        sql_citado("SELECT * FROM {} WHERE id = ?", citar(tabela)),
        (identificador,),
    ).fetchone()
    if row is None:
        raise ErroConsulta(404, "Linha não encontrada.")
    return serializar(row, tipos)


def atualizar_linha(
    conn: sqlite3.Connection,
    tabela: str,
    identificador: int,
    valores: dict[str, Any],
) -> dict[str, Any]:
    """Atualiza as colunas informadas e devolve a linha resultante."""
    exigir_tabela(conn, tabela)
    tipos = tipos_usuario(conn, tabela)
    limpos = conferir_linha(tipos, valores, parcial=True)
    atribuicoes = ", ".join(f"{citar(coluna)} = ?" for coluna in limpos)
    cur = executar_sql(
        conn,
        sql_citado("UPDATE {} SET {} WHERE id = ?", citar(tabela), atribuicoes),
        [*limpos.values(), identificador],
    )
    if cur.rowcount == 0:
        raise ErroConsulta(404, "Linha não encontrada.")
    return obter_linha(conn, tabela, identificador)


def apagar_linha(conn: sqlite3.Connection, tabela: str, identificador: int) -> None:
    """Remove a linha pelo id, ou responde 404 se ela não existir."""
    exigir_tabela(conn, tabela)
    cur = executar_sql(
        conn,
        sql_citado("DELETE FROM {} WHERE id = ?", citar(tabela)),
        (identificador,),
    )
    if cur.rowcount == 0:
        raise ErroConsulta(404, "Linha não encontrada.")


def _inserir(conn: sqlite3.Connection, tabela: str, valores: dict[str, Any]) -> int:
    if not valores:
        cur = executar_sql(
            conn, sql_citado("INSERT INTO {} DEFAULT VALUES", citar(tabela))
        )
    else:
        colunas = ", ".join(citar(coluna) for coluna in valores)
        marcas = ", ".join("?" for _ in valores)
        cur = executar_sql(
            conn,
            sql_citado(
                "INSERT INTO {} ({}) VALUES ({})",
                citar(tabela),
                colunas,
                marcas,
            ),
            list(valores.values()),
        )
    if cur.lastrowid is None:
        raise ErroConsulta(400, "Não foi possível gravar a linha.")
    return int(cur.lastrowid)


def _livro(
    titulo: str,
    autor: str,
    ano: int,
    genero: str,
    preco: float,
) -> dict[str, Any]:
    return {
        "titulo": titulo,
        "autor": autor,
        "ano": ano,
        "genero": genero,
        "preco": preco,
    }
