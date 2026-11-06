"""Listagem, filtros e SELECT somente leitura."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

from datalink.domain.erros import ErroConsulta
from datalink.infrastructure.sqlite_meta import (
    executar_sql,
    exigir_tabela,
    sql_citado,
    tipos_completos,
)
from datalink.infrastructure.sqlite_valores import (
    colunas_select,
    converter,
    deslocamento_linhas,
    limite_linhas,
    parametro_sql,
    serializar,
)
from datalink.validation.nomes import (
    OPERADORES_ORDEM,
    OPERADORES_TEXTO,
    citar,
    validar_select,
)

LIMITE_FILTROS = 20
LIMITE_ORDEM = 5
LIMITE_EM = 100
LIMITE_PARAMETROS = 50
LIMITE_LINHAS_SQL = 500
_SIMBOLOS = {
    "igual": "=",
    "diferente": "!=",
    "maior": ">",
    "menor": "<",
    "maior_igual": ">=",
    "menor_igual": "<=",
}


def listar_linhas(
    conn: sqlite3.Connection,
    tabela: str,
    *,
    filtros: list[dict[str, Any]] | None = None,
    ordenar: list[dict[str, str]] | None = None,
    colunas: list[str] | None = None,
    limite: int = 50,
    deslocamento: int = 0,
    filtros_texto: bool = False,
) -> dict[str, Any]:
    """Lista linhas com filtro, ordem, colunas, limite e deslocamento."""
    exigir_tabela(conn, tabela)
    limite = limite_linhas(limite)
    deslocamento = deslocamento_linhas(deslocamento)
    tipos = tipos_completos(conn, tabela)
    selecionadas = colunas_select(colunas, tipos)
    where, params = _where(filtros or [], tipos, filtros_texto=filtros_texto)
    ordem = _order(ordenar, tipos)
    total = executar_sql(
        conn,
        sql_citado("SELECT COUNT(*) AS n FROM {}{}", citar(tabela), where),
        params,
    ).fetchone()["n"]
    lista_colunas = ", ".join(citar(coluna) for coluna in selecionadas)
    rows = executar_sql(
        conn,
        sql_citado(
            "SELECT {} FROM {}{}{} LIMIT ? OFFSET ?",
            lista_colunas,
            citar(tabela),
            where,
            ordem,
        ),
        [*params, limite, deslocamento],
    ).fetchall()
    return {
        "tabela": tabela,
        "total": int(total),
        "limite": limite,
        "deslocamento": deslocamento,
        "linhas": [serializar(row, tipos) for row in rows],
    }


def executar_select(
    caminho: Path,
    sql: str,
    parametros: list[Any],
    *,
    limite_s: float = 2.0,
) -> dict[str, Any]:
    """Roda um SELECT em modo somente leitura, com teto de tempo e de linhas."""
    consulta = validar_select(sql)
    params = [parametro_sql(valor) for valor in parametros]
    if len(params) > LIMITE_PARAMETROS:
        raise ErroConsulta(400, "Use no máximo 50 parâmetros.")
    conn = _conexao_leitura(caminho)
    inicio = time.monotonic()

    def interromper() -> int:
        return 1 if time.monotonic() - inicio > limite_s else 0

    conn.set_progress_handler(interromper, 1000)
    try:
        return _ler_select(conn, consulta, params)
    finally:
        conn.close()


def _conexao_leitura(caminho: Path) -> sqlite3.Connection:
    uri = "file:" + quote(str(caminho)) + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ler_select(
    conn: sqlite3.Connection,
    consulta: str,
    params: list[Any],
) -> dict[str, Any]:
    try:
        cur = conn.execute(consulta, params)
    except sqlite3.ProgrammingError as exc:
        raise ErroConsulta(400, "Envie uma única consulta SELECT.") from exc
    except sqlite3.Error as exc:
        raise _erro_select(exc) from exc
    brutas = cur.fetchmany(LIMITE_LINHAS_SQL + 1)
    colunas = [item[0] for item in cur.description] if cur.description else []
    linhas = [dict(linha) for linha in brutas[:LIMITE_LINHAS_SQL]]
    return {
        "colunas": colunas,
        "linhas": linhas,
        "truncado": len(brutas) > LIMITE_LINHAS_SQL,
    }


def _erro_select(exc: sqlite3.Error) -> ErroConsulta:
    if "interrupted" in str(exc).lower():
        return ErroConsulta(400, "A consulta excedeu o tempo limite.")
    return ErroConsulta(400, "Não foi possível executar o SELECT.")


def _where(
    filtros: list[dict[str, Any]],
    tipos: dict[str, dict[str, Any]],
    *,
    filtros_texto: bool,
) -> tuple[str, list[Any]]:
    if len(filtros) > LIMITE_FILTROS:
        raise ErroConsulta(400, "Use no máximo 20 filtros.")
    clausulas: list[str] = []
    params: list[Any] = []
    for filtro in filtros:
        clausula, novos = _clausula(filtro, tipos, filtros_texto=filtros_texto)
        clausulas.append(clausula)
        params.extend(novos)
    if not clausulas:
        return "", params
    return " WHERE " + " AND ".join(clausulas), params


def _clausula(
    filtro: dict[str, Any],
    tipos: dict[str, dict[str, Any]],
    *,
    filtros_texto: bool,
) -> tuple[str, list[Any]]:
    _coluna, op, tipo, citado = _alvo(filtro, tipos)
    if op in {"nulo", "nao_nulo"}:
        return _clausula_nulo(op, citado, filtro.get("valor"))
    if op == "em":
        return _clausula_em(
            tipo, citado, filtro.get("valor"), filtros_texto=filtros_texto
        )
    if op in OPERADORES_TEXTO:
        return _clausula_texto(
            tipo, citado, op, filtro.get("valor"), filtros_texto=filtros_texto
        )
    if op in _SIMBOLOS:
        return _clausula_comparacao(
            tipo, citado, op, filtro.get("valor"), filtros_texto=filtros_texto
        )
    raise ErroConsulta(400, f"Operador desconhecido: {op}.")


def _alvo(
    filtro: dict[str, Any],
    tipos: dict[str, dict[str, Any]],
) -> tuple[str, str, str, str]:
    coluna = filtro.get("coluna")
    op = filtro.get("op", "igual")
    if coluna not in tipos:
        raise ErroConsulta(400, f"Coluna desconhecida no filtro: {coluna}.")
    if not isinstance(op, str):
        raise ErroConsulta(400, "Operador de filtro inválido.")
    tipo = tipos[coluna]["tipo"]
    if op in OPERADORES_TEXTO and tipo != "texto":
        raise ErroConsulta(400, f"O operador {op} só vale para texto.")
    if op in OPERADORES_ORDEM and tipo == "booleano":
        raise ErroConsulta(400, f"O operador {op} não vale para booleano.")
    return str(coluna), op, tipo, citar(str(coluna))


def _clausula_nulo(op: str, citado: str, valor: Any) -> tuple[str, list[Any]]:
    if valor is not None:
        raise ErroConsulta(400, f"O operador {op} não usa valor.")
    sufixo = "NOT " if op == "nao_nulo" else ""
    return f"{citado} IS {sufixo}NULL", []


def _clausula_em(
    tipo: str,
    citado: str,
    valores: Any,
    *,
    filtros_texto: bool,
) -> tuple[str, list[Any]]:
    if not isinstance(valores, list) or not valores or len(valores) > LIMITE_EM:
        raise ErroConsulta(400, "O operador em exige uma lista de 1 a 100 valores.")
    convertidos = [
        converter(tipo, item, obrigatorio=True, texto=filtros_texto) for item in valores
    ]
    marcas = ", ".join("?" for _ in convertidos)
    return f"{citado} IN ({marcas})", convertidos


def _clausula_texto(
    tipo: str,
    citado: str,
    op: str,
    valor: Any,
    *,
    filtros_texto: bool,
) -> tuple[str, list[Any]]:
    convertido = converter(tipo, valor, obrigatorio=True, texto=filtros_texto)
    return f"{citado} LIKE ? ESCAPE '\\'", [_like(str(convertido), op)]


def _clausula_comparacao(
    tipo: str,
    citado: str,
    op: str,
    valor: Any,
    *,
    filtros_texto: bool,
) -> tuple[str, list[Any]]:
    convertido = converter(tipo, valor, obrigatorio=True, texto=filtros_texto)
    return f"{citado} {_SIMBOLOS[op]} ?", [convertido]


def _like(valor: str, op: str) -> str:
    escapado = valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    if op == "contem":
        return f"%{escapado}%"
    if op == "comeca_com":
        return f"{escapado}%"
    return f"%{escapado}"


def _order(
    ordenar: list[dict[str, str]] | None, tipos: dict[str, dict[str, Any]]
) -> str:
    if not ordenar:
        return " ORDER BY " + citar("id") + " ASC"
    if len(ordenar) > LIMITE_ORDEM:
        raise ErroConsulta(400, "Ordene por no máximo 5 colunas.")
    return " ORDER BY " + ", ".join(_parte_ordem(item, tipos) for item in ordenar)


def _parte_ordem(item: dict[str, str], tipos: dict[str, dict[str, Any]]) -> str:
    coluna = item.get("coluna")
    direcao = item.get("direcao", "asc")
    if coluna not in tipos:
        raise ErroConsulta(400, f"Coluna desconhecida na ordenação: {coluna}.")
    if direcao not in {"asc", "desc"}:
        raise ErroConsulta(400, "Direção precisa ser asc ou desc.")
    return f"{citar(str(coluna))} {direcao.upper()}"
