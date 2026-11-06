"""Conexão, catálogo e esquema das tabelas SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from datalink.domain.erros import ErroConsulta
from datalink.validation.nomes import (
    COLUNAS_SISTEMA,
    citar,
    validar_nome,
    validar_nome_coluna,
)

TIPOS_SQLITE = {
    "texto": "TEXT",
    "inteiro": "INTEGER",
    "decimal": "REAL",
    "booleano": "INTEGER",
}
LIMITE_COLUNAS = 32


def sql_citado(modelo: str, *trechos: str) -> str:
    """Monta SQL com trechos já citados. Valores continuam em placeholder."""
    return modelo.format(*trechos)


def executar_sql(
    conn: sqlite3.Connection,
    consulta: str,
    parametros: tuple[Any, ...] | list[Any] = (),
) -> sqlite3.Cursor:
    """Executa SQL com identificadores já citados e valores em placeholder."""
    return conn.execute(consulta, parametros)


def conectar(caminho: Path) -> sqlite3.Connection:
    """Abre o SQLite com chave estrangeira, WAL e espera de 5 segundos."""
    conn = sqlite3.connect(caminho, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def preparar(conn: sqlite3.Connection) -> None:
    """Cria o catálogo interno de colunas, se ainda não existir."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS "_banco_colunas" (
            tabela TEXT NOT NULL,
            coluna TEXT NOT NULL,
            tipo TEXT NOT NULL,
            obrigatorio INTEGER NOT NULL,
            posicao INTEGER NOT NULL,
            PRIMARY KEY (tabela, coluna)
        )
        """
    )


def listar_tabelas(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Lista as tabelas de usuário com o esquema de cada uma."""
    linhas = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
          AND name NOT LIKE '_banco_%'
        ORDER BY name
        """
    ).fetchall()
    return [esquema(conn, linha["name"]) for linha in linhas]


def esquema(conn: sqlite3.Connection, tabela: str) -> dict[str, Any]:
    """Devolve o nome da tabela e a descrição das colunas."""
    exigir_tabela(conn, tabela)
    return {"nome": tabela, "colunas": descrever_colunas(conn, tabela)}


def criar_tabela(
    conn: sqlite3.Connection,
    nome: str,
    colunas: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cria a tabela física e grava o tipo de cada coluna no catálogo."""
    validar_nome(nome, o_que="Tabela")
    _exigir_colunas(colunas)
    if tabela_existe(conn, nome):
        raise ErroConsulta(409, f"A tabela {nome} já existe.")
    conn.execute('DELETE FROM "_banco_colunas" WHERE tabela = ?', (nome,))
    definicoes = _definicoes(conn, nome, colunas)
    executar_sql(
        conn,
        sql_citado("CREATE TABLE {} ({})", citar(nome), ", ".join(definicoes)),
    )
    return esquema(conn, nome)


def apagar_tabela(conn: sqlite3.Connection, nome: str) -> None:
    """Remove a tabela física e o catálogo, ou só o resíduo que restar."""
    validar_nome(nome, o_que="Tabela")
    existe_fisica = tabela_existe(conn, nome)
    meta = conn.execute(
        'SELECT 1 FROM "_banco_colunas" WHERE tabela = ? LIMIT 1',
        (nome,),
    ).fetchone()
    if not existe_fisica and not meta:
        raise ErroConsulta(404, f"Tabela {nome} não encontrada.")
    conn.execute('DELETE FROM "_banco_colunas" WHERE tabela = ?', (nome,))
    if existe_fisica:
        executar_sql(conn, sql_citado("DROP TABLE {}", citar(nome)))


def tabela_existe(conn: sqlite3.Connection, nome: str) -> bool:
    """Diz se há uma tabela de usuário com esse nome."""
    row = conn.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = ?
          AND name NOT LIKE 'sqlite_%'
          AND name NOT LIKE '_banco_%'
        """,
        (nome,),
    ).fetchone()
    return row is not None


def exigir_tabela(conn: sqlite3.Connection, nome: str) -> str:
    """Valida o nome e recusa tabela ausente."""
    validar_nome(nome, o_que="Tabela")
    if not tabela_existe(conn, nome):
        raise ErroConsulta(404, f"Tabela {nome} não encontrada.")
    return nome


def tipos_usuario(conn: sqlite3.Connection, tabela: str) -> dict[str, dict[str, Any]]:
    """Lê tipo e obrigatoriedade das colunas criadas pelo usuário."""
    rows = conn.execute(
        """
        SELECT coluna, tipo, obrigatorio
        FROM "_banco_colunas"
        WHERE tabela = ?
        ORDER BY posicao
        """,
        (tabela,),
    ).fetchall()
    if not rows:
        raise ErroConsulta(404, f"Tabela {tabela} não encontrada.")
    return {
        row["coluna"]: {"tipo": row["tipo"], "obrigatorio": bool(row["obrigatorio"])}
        for row in rows
    }


def tipos_completos(conn: sqlite3.Connection, tabela: str) -> dict[str, dict[str, Any]]:
    """Inclui id e criado_em na frente das colunas do usuário."""
    usuario = tipos_usuario(conn, tabela)
    return {
        "id": {"tipo": "inteiro", "obrigatorio": True},
        "criado_em": {"tipo": "texto", "obrigatorio": True},
        **usuario,
    }


def descrever_colunas(conn: sqlite3.Connection, tabela: str) -> list[dict[str, Any]]:
    """Descreve cada coluna, marcando as que pertencem ao sistema."""
    tipos = tipos_completos(conn, tabela)
    return [
        {
            "nome": nome,
            "tipo": info["tipo"],
            "obrigatorio": info["obrigatorio"],
            "sistema": nome in COLUNAS_SISTEMA,
        }
        for nome, info in tipos.items()
    ]


def _exigir_colunas(colunas: list[dict[str, Any]]) -> None:
    if not colunas:
        raise ErroConsulta(400, "Informe ao menos uma coluna.")
    if len(colunas) > LIMITE_COLUNAS:
        raise ErroConsulta(400, "Uma tabela aceita no máximo 32 colunas.")


def _definicoes(
    conn: sqlite3.Connection,
    nome: str,
    colunas: list[dict[str, Any]],
) -> list[str]:
    definicoes = [
        '"id" INTEGER PRIMARY KEY AUTOINCREMENT',
        "\"criado_em\" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
    ]
    vistos: set[str] = set()
    for indice, coluna in enumerate(colunas):
        definicoes.append(_definicao_coluna(conn, nome, coluna, indice, vistos))
    return definicoes


def _definicao_coluna(
    conn: sqlite3.Connection,
    tabela: str,
    coluna: dict[str, Any],
    indice: int,
    vistos: set[str],
) -> str:
    nome_coluna = validar_nome_coluna(str(coluna["nome"]))
    chave = nome_coluna.lower()
    if chave in vistos:
        raise ErroConsulta(400, f"Coluna repetida: {nome_coluna}.")
    vistos.add(chave)
    tipo = coluna["tipo"]
    if tipo not in TIPOS_SQLITE:
        raise ErroConsulta(400, f"Tipo inválido na coluna {nome_coluna}.")
    obrigatorio = bool(coluna.get("obrigatorio", False))
    nulo = " NOT NULL" if obrigatorio else ""
    conn.execute(
        """
        INSERT INTO "_banco_colunas"
            (tabela, coluna, tipo, obrigatorio, posicao)
        VALUES (?, ?, ?, ?, ?)
        """,
        (tabela, nome_coluna, tipo, int(obrigatorio), indice),
    )
    return f"{citar(nome_coluna)} {TIPOS_SQLITE[tipo]}{nulo}"
