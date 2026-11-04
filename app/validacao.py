"""Regras de nome, tipo e SQL somente leitura."""

from __future__ import annotations

import re

from app.erros import ErroConsulta

NOME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,47}$")
TIPOS = ("texto", "inteiro", "decimal", "booleano")
COLUNAS_SISTEMA = ("id", "criado_em")
PREFIXOS_INTERNOS = ("sqlite_", "_banco_")

OPERADORES = (
    "igual",
    "diferente",
    "contem",
    "comeca_com",
    "termina_com",
    "maior",
    "menor",
    "maior_igual",
    "menor_igual",
    "em",
    "nulo",
    "nao_nulo",
)

OPERADORES_TEXTO = {"contem", "comeca_com", "termina_com"}
OPERADORES_ORDEM = {"maior", "menor", "maior_igual", "menor_igual"}

_PROIBIDOS_SQL = {
    "attach",
    "detach",
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "vacuum",
    "reindex",
    "pragma",
    "begin",
    "commit",
    "rollback",
    "savepoint",
    "release",
    "trigger",
    "grant",
    "revoke",
    "analyze",
    "into",
    "load_extension",
    "transaction",
}


def validar_nome(nome: str, *, o_que: str = "Nome") -> str:
    if not isinstance(nome, str) or not NOME.fullmatch(nome):
        raise ErroConsulta(
            400,
            f"{o_que} inválido. Use de 1 a 48 caracteres: letras, números e _.",
        )
    if nome.lower().startswith(PREFIXOS_INTERNOS):
        raise ErroConsulta(
            400,
            f"{o_que} não pode começar com sqlite_ nem _banco_.",
        )
    return nome


def validar_nome_coluna(nome: str) -> str:
    validar_nome(nome, o_que="Coluna")
    if nome.lower() in COLUNAS_SISTEMA:
        raise ErroConsulta(400, f"A coluna {nome} é reservada pelo banco.")
    return nome


def citar(nome: str) -> str:
    validar_nome(nome)
    return '"' + nome.replace('"', '""') + '"'


def validar_select(sql: str) -> str:
    if not isinstance(sql, str):
        raise ErroConsulta(400, "O SQL precisa ser um texto.")
    if "\x00" in sql:
        raise ErroConsulta(400, "O SQL contém um caractere inválido.")
    if len(sql) > 5000:
        raise ErroConsulta(400, "O SQL passa de 5000 caracteres.")

    mascarado = _mascarar_sql(sql)
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", mascarado)
    if not tokens or tokens[0].lower() not in {"select", "with"}:
        raise ErroConsulta(400, "Só consultas SELECT (ou WITH ... SELECT) são aceitas.")
    if ";" in mascarado:
        raise ErroConsulta(400, "Envie uma única consulta, sem ponto e vírgula.")

    for token in tokens:
        palavra = token.lower()
        if palavra in _PROIBIDOS_SQL:
            raise ErroConsulta(400, f"A palavra {palavra} não é permitida nesta consulta.")
        if palavra.startswith("sqlite_") and palavra != "sqlite_version":
            raise ErroConsulta(400, "Funções internas do SQLite não são permitidas.")

    if "_banco_" in mascarado.lower():
        raise ErroConsulta(400, "Tabelas internas do banco não entram na consulta.")
    return sql.strip()


def _mascarar_sql(sql: str) -> str:
    """Tira textos, comentários e identificadores entre aspas para a checagem."""
    saida: list[str] = []
    i = 0
    n = len(sql)
    while i < n:
        par = sql[i : i + 2]
        if par == "--":
            fim = sql.find("\n", i)
            i = n if fim == -1 else fim
            continue
        if par == "/*":
            fim = sql.find("*/", i + 2)
            if fim == -1:
                raise ErroConsulta(400, "Comentário /* sem fechamento.")
            i = fim + 2
            saida.append(" ")
            continue
        caractere = sql[i]
        if caractere in {"'", '"'}:
            i += 1
            while i < n:
                if sql[i] == caractere:
                    if i + 1 < n and sql[i + 1] == caractere:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            else:
                raise ErroConsulta(400, "Aspas sem fechamento no SQL.")
            saida.append(" ident ")
            continue
        saida.append(caractere)
        i += 1
    return "".join(saida)
