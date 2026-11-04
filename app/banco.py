"""Persistência SQLite: tabelas, linhas e consultas parametrizadas."""

from __future__ import annotations

import math
import os
import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.erros import ErroConsulta
from app.validacao import (
    COLUNAS_SISTEMA,
    OPERADORES_ORDEM,
    OPERADORES_TEXTO,
    citar,
    validar_nome,
    validar_nome_coluna,
    validar_select,
)

TIPOS_SQLITE = {
    "texto": "TEXT",
    "inteiro": "INTEGER",
    "decimal": "REAL",
    "booleano": "INTEGER",
}

META = '"_banco_colunas"'

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


def caminho_padrao() -> Path:
    bruto = os.environ.get("BANCO_CAMINHO", "data/banco.db")
    caminho = Path(bruto).expanduser().resolve()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return caminho


def conectar(caminho: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(caminho, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def preparar(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {META} (
            tabela TEXT NOT NULL,
            coluna TEXT NOT NULL,
            tipo TEXT NOT NULL,
            obrigatorio INTEGER NOT NULL,
            posicao INTEGER NOT NULL,
            PRIMARY KEY (tabela, coluna)
        )
        """
    )


def semear(conn: sqlite3.Connection) -> None:
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
    inserir_linhas(
        conn,
        "livros",
        [
            {
                "titulo": titulo,
                "autor": autor,
                "ano": ano,
                "genero": genero,
                "preco": preco,
            }
            for titulo, autor, ano, genero, preco in LIVROS
        ],
    )


def listar_tabelas(conn: sqlite3.Connection) -> list[dict[str, Any]]:
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
    exigir_tabela(conn, tabela)
    return {"nome": tabela, "colunas": descrever_colunas(conn, tabela)}


def _limpar_residuos_tabela(conn: sqlite3.Connection, nome: str) -> None:
    """Remove metadados e/ou tabela física órfãos para evitar 404/409 dessincronizados."""
    conn.execute(f"DELETE FROM {META} WHERE tabela = ?", (nome,))
    if tabela_existe(conn, nome):
        conn.execute(f"DROP TABLE {citar(nome)}")


def criar_tabela(
    conn: sqlite3.Connection,
    nome: str,
    colunas: list[dict[str, Any]],
) -> dict[str, Any]:
    validar_nome(nome, o_que="Tabela")
    if not colunas:
        raise ErroConsulta(400, "Informe ao menos uma coluna.")
    if len(colunas) > 32:
        raise ErroConsulta(400, "Uma tabela aceita no máximo 32 colunas.")
    if tabela_existe(conn, nome):
        raise ErroConsulta(409, f"A tabela {nome} já existe.")
    # Metadado órfão sem tabela física: limpa antes de recriar.
    conn.execute(f"DELETE FROM {META} WHERE tabela = ?", (nome,))

    vistos: set[str] = set()
    definicoes = [
        '"id" INTEGER PRIMARY KEY AUTOINCREMENT',
        "\"criado_em\" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
    ]
    for indice, coluna in enumerate(colunas):
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
        definicoes.append(f"{citar(nome_coluna)} {TIPOS_SQLITE[tipo]}{nulo}")
        conn.execute(
            f"INSERT INTO {META} (tabela, coluna, tipo, obrigatorio, posicao) VALUES (?, ?, ?, ?, ?)",
            (nome, nome_coluna, tipo, int(obrigatorio), indice),
        )

    conn.execute(f"CREATE TABLE {citar(nome)} ({', '.join(definicoes)})")
    return esquema(conn, nome)


def apagar_tabela(conn: sqlite3.Connection, nome: str) -> None:
    validar_nome(nome, o_que="Tabela")
    existe_fisica = tabela_existe(conn, nome)
    meta = conn.execute(
        f"SELECT 1 FROM {META} WHERE tabela = ? LIMIT 1",
        (nome,),
    ).fetchone()
    if not existe_fisica and not meta:
        raise ErroConsulta(404, f"Tabela {nome} não encontrada.")
    _limpar_residuos_tabela(conn, nome)


def inserir_linhas(
    conn: sqlite3.Connection,
    tabela: str,
    linhas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    exigir_tabela(conn, tabela)
    if not linhas:
        raise ErroConsulta(400, "Informe ao menos uma linha.")
    if len(linhas) > 200:
        raise ErroConsulta(400, "O máximo por envio é 200 linhas.")
    tipos = tipos_usuario(conn, tabela)
    ids: list[int] = []
    for linha in linhas:
        valores = conferir_linha(tipos, linha, parcial=False)
        ids.append(_inserir(conn, tabela, valores))
    return [obter_linha(conn, tabela, identificador) for identificador in ids]


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
    exigir_tabela(conn, tabela)
    limite = _limite(limite)
    deslocamento = _deslocamento(deslocamento)
    tipos = tipos_completos(conn, tabela)
    selecionadas = _colunas_select(colunas, tipos)
    where, params = _where(filtros or [], tipos, filtros_texto=filtros_texto)
    ordem = _order(ordenar, tipos)
    total = conn.execute(
        f"SELECT COUNT(*) AS n FROM {citar(tabela)}{where}",
        params,
    ).fetchone()["n"]
    lista_colunas = ", ".join(citar(coluna) for coluna in selecionadas)
    rows = conn.execute(
        f"SELECT {lista_colunas} FROM {citar(tabela)}{where}{ordem} LIMIT ? OFFSET ?",
        [*params, limite, deslocamento],
    ).fetchall()
    return {
        "tabela": tabela,
        "total": int(total),
        "limite": limite,
        "deslocamento": deslocamento,
        "linhas": [_serializar(row, tipos) for row in rows],
    }


def obter_linha(conn: sqlite3.Connection, tabela: str, identificador: int) -> dict[str, Any]:
    exigir_tabela(conn, tabela)
    tipos = tipos_completos(conn, tabela)
    row = conn.execute(
        f"SELECT * FROM {citar(tabela)} WHERE id = ?",
        (identificador,),
    ).fetchone()
    if row is None:
        raise ErroConsulta(404, "Linha não encontrada.")
    return _serializar(row, tipos)


def atualizar_linha(
    conn: sqlite3.Connection,
    tabela: str,
    identificador: int,
    valores: dict[str, Any],
) -> dict[str, Any]:
    exigir_tabela(conn, tabela)
    tipos = tipos_usuario(conn, tabela)
    limpos = conferir_linha(tipos, valores, parcial=True)
    atribuicoes = ", ".join(f"{citar(coluna)} = ?" for coluna in limpos)
    cur = conn.execute(
        f"UPDATE {citar(tabela)} SET {atribuicoes} WHERE id = ?",
        [*limpos.values(), identificador],
    )
    if cur.rowcount == 0:
        raise ErroConsulta(404, "Linha não encontrada.")
    return obter_linha(conn, tabela, identificador)


def apagar_linha(conn: sqlite3.Connection, tabela: str, identificador: int) -> None:
    exigir_tabela(conn, tabela)
    cur = conn.execute(
        f"DELETE FROM {citar(tabela)} WHERE id = ?",
        (identificador,),
    )
    if cur.rowcount == 0:
        raise ErroConsulta(404, "Linha não encontrada.")


def executar_select(caminho: Path, sql: str, parametros: list[Any]) -> dict[str, Any]:
    consulta = validar_select(sql)
    params = [_parametro_sql(valor) for valor in parametros]
    if len(params) > 50:
        raise ErroConsulta(400, "Use no máximo 50 parâmetros.")

    uri = "file:" + quote(str(caminho)) + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    inicio = time.monotonic()
    limite_s = float(os.environ.get("BANCO_SQL_SEGUNDOS", "2"))

    def interromper() -> int:
        return 1 if time.monotonic() - inicio > limite_s else 0

    conn.set_progress_handler(interromper, 1000)
    try:
        try:
            cur = conn.execute(consulta, params)
        except sqlite3.ProgrammingError as exc:
            raise ErroConsulta(400, "Envie uma única consulta SELECT.") from exc
        except sqlite3.Error as exc:
            mensagem = str(exc).lower()
            if "interrupted" in mensagem:
                raise ErroConsulta(400, "A consulta excedeu o tempo limite.") from exc
            raise ErroConsulta(400, "Não foi possível executar o SELECT.") from exc
        brutas = cur.fetchmany(501)
        colunas = [item[0] for item in cur.description] if cur.description else []
    finally:
        conn.close()

    linhas = [dict(linha) for linha in brutas[:500]]
    return {"colunas": colunas, "linhas": linhas, "truncado": len(brutas) > 500}


def tabela_existe(conn: sqlite3.Connection, nome: str) -> bool:
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
    validar_nome(nome, o_que="Tabela")
    if not tabela_existe(conn, nome):
        raise ErroConsulta(404, f"Tabela {nome} não encontrada.")
    return nome


def tipos_usuario(conn: sqlite3.Connection, tabela: str) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        f"SELECT coluna, tipo, obrigatorio FROM {META} WHERE tabela = ? ORDER BY posicao",
        (tabela,),
    ).fetchall()
    if not rows:
        raise ErroConsulta(404, f"Tabela {tabela} não encontrada.")
    return {
        row["coluna"]: {"tipo": row["tipo"], "obrigatorio": bool(row["obrigatorio"])}
        for row in rows
    }


def tipos_completos(conn: sqlite3.Connection, tabela: str) -> dict[str, dict[str, Any]]:
    usuario = tipos_usuario(conn, tabela)
    return {
        "id": {"tipo": "inteiro", "obrigatorio": True},
        "criado_em": {"tipo": "texto", "obrigatorio": True},
        **usuario,
    }


def descrever_colunas(conn: sqlite3.Connection, tabela: str) -> list[dict[str, Any]]:
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


def conferir_linha(
    tipos: dict[str, dict[str, Any]],
    valores: dict[str, Any],
    *,
    parcial: bool,
) -> dict[str, Any]:
    if not isinstance(valores, dict):
        raise ErroConsulta(400, "Cada linha precisa ser um objeto JSON.")
    desconhecidas = [coluna for coluna in valores if coluna not in tipos]
    if desconhecidas:
        raise ErroConsulta(400, "Colunas desconhecidas: " + ", ".join(desconhecidas) + ".")
    if not parcial and not valores and any(info["obrigatorio"] for info in tipos.values()):
        raise ErroConsulta(400, "Informe as colunas obrigatórias.")

    saida: dict[str, Any] = {}
    nomes = valores.keys() if parcial else [nome for nome in tipos if nome in valores]
    if parcial and not valores:
        raise ErroConsulta(400, "Informe ao menos uma coluna para atualizar.")
    for nome in nomes:
        info = tipos[nome]
        saida[nome] = converter(info["tipo"], valores[nome], obrigatorio=info["obrigatorio"])
    if not parcial:
        faltando = [
            nome
            for nome, info in tipos.items()
            if info["obrigatorio"] and nome not in valores
        ]
        if faltando:
            raise ErroConsulta(
                400,
                "Colunas obrigatórias ausentes: " + ", ".join(faltando) + ".",
            )
    return saida


def converter(tipo: str, valor: Any, *, obrigatorio: bool, texto: bool = False) -> Any:
    if texto and isinstance(valor, str):
        valor = _coagir_texto(tipo, valor)
    if valor is None:
        if obrigatorio:
            raise ErroConsulta(400, "Coluna obrigatória não aceita nulo.")
        return None
    if tipo == "texto":
        if not isinstance(valor, str):
            raise ErroConsulta(400, "Valor de texto inválido.")
        if len(valor) > 10_000:
            raise ErroConsulta(400, "Texto maior que 10000 caracteres.")
        return valor
    if tipo == "inteiro":
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise ErroConsulta(400, "Valor inteiro inválido.")
        if abs(valor) > 2**63 - 1:
            raise ErroConsulta(400, "Inteiro fora do intervalo do SQLite.")
        return valor
    if tipo == "decimal":
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ErroConsulta(400, "Valor decimal inválido.")
        numero = float(valor)
        if not math.isfinite(numero):
            raise ErroConsulta(400, "Valor decimal inválido.")
        return numero
    if tipo == "booleano":
        if not isinstance(valor, bool):
            raise ErroConsulta(400, "Valor booleano inválido. Use true ou false.")
        return valor
    raise ErroConsulta(400, "Tipo de coluna desconhecido.")


def _coagir_texto(tipo: str, valor: str) -> Any:
    if valor == "" or valor.lower() == "null":
        return None
    if tipo == "texto":
        return valor
    if tipo == "inteiro":
        try:
            return int(valor)
        except ValueError as exc:
            raise ErroConsulta(400, f"Não foi possível ler o inteiro {valor!r}.") from exc
    if tipo == "decimal":
        try:
            return float(valor)
        except ValueError as exc:
            raise ErroConsulta(400, f"Não foi possível ler o decimal {valor!r}.") from exc
    if tipo == "booleano":
        mapa = {"true": True, "false": False, "1": True, "0": False}
        if valor.lower() not in mapa:
            raise ErroConsulta(400, "Booleano na URL aceita true, false, 1 ou 0.")
        return mapa[valor.lower()]
    raise ErroConsulta(400, "Tipo de coluna desconhecido.")


def _inserir(conn: sqlite3.Connection, tabela: str, valores: dict[str, Any]) -> int:
    if not valores:
        cur = conn.execute(f"INSERT INTO {citar(tabela)} DEFAULT VALUES")
    else:
        colunas = ", ".join(citar(coluna) for coluna in valores)
        marcas = ", ".join("?" for _ in valores)
        cur = conn.execute(
            f"INSERT INTO {citar(tabela)} ({colunas}) VALUES ({marcas})",
            list(valores.values()),
        )
    if cur.lastrowid is None:
        raise ErroConsulta(400, "Não foi possível gravar a linha.")
    return int(cur.lastrowid)


def _colunas_select(pedidas: list[str] | None, tipos: dict[str, dict[str, Any]]) -> list[str]:
    if not pedidas:
        return list(tipos)
    if len(pedidas) > 32:
        raise ErroConsulta(400, "Selecione no máximo 32 colunas.")
    saida: list[str] = []
    for nome in pedidas:
        if nome not in tipos:
            raise ErroConsulta(400, f"Coluna desconhecida: {nome}.")
        if nome not in saida:
            saida.append(nome)
    return saida


def _where(
    filtros: list[dict[str, Any]],
    tipos: dict[str, dict[str, Any]],
    *,
    filtros_texto: bool,
) -> tuple[str, list[Any]]:
    if len(filtros) > 20:
        raise ErroConsulta(400, "Use no máximo 20 filtros.")
    clausulas: list[str] = []
    params: list[Any] = []
    for filtro in filtros:
        coluna = filtro.get("coluna")
        op = filtro.get("op", "igual")
        if coluna not in tipos:
            raise ErroConsulta(400, f"Coluna desconhecida no filtro: {coluna}.")
        if not isinstance(op, str):
            raise ErroConsulta(400, "Operador de filtro inválido.")
        tipo = tipos[coluna]["tipo"]
        citado = citar(coluna)
        if op in OPERADORES_TEXTO and tipo != "texto":
            raise ErroConsulta(400, f"O operador {op} só vale para texto.")
        if op in OPERADORES_ORDEM and tipo == "booleano":
            raise ErroConsulta(400, f"O operador {op} não vale para booleano.")
        if op in {"nulo", "nao_nulo"}:
            if filtro.get("valor") is not None:
                raise ErroConsulta(400, f"O operador {op} não usa valor.")
            clausulas.append(f"{citado} IS {'NOT ' if op == 'nao_nulo' else ''}NULL")
            continue
        if op == "em":
            valores = filtro.get("valor")
            if not isinstance(valores, list) or not valores or len(valores) > 100:
                raise ErroConsulta(400, "O operador em exige uma lista de 1 a 100 valores.")
            convertidos = [
                converter(tipo, item, obrigatorio=True, texto=filtros_texto) for item in valores
            ]
            marcas = ", ".join("?" for _ in convertidos)
            clausulas.append(f"{citado} IN ({marcas})")
            params.extend(convertidos)
            continue
        if op not in {"igual", "diferente", "contem", "comeca_com", "termina_com", *OPERADORES_ORDEM}:
            raise ErroConsulta(400, f"Operador desconhecido: {op}.")
        valor = converter(tipo, filtro.get("valor"), obrigatorio=True, texto=filtros_texto)
        if op in OPERADORES_TEXTO:
            valor = _like(str(valor), op)
            clausulas.append(f"{citado} LIKE ? ESCAPE '\\'")
            params.append(valor)
            continue
        simbolo = {
            "igual": "=",
            "diferente": "!=",
            "maior": ">",
            "menor": "<",
            "maior_igual": ">=",
            "menor_igual": "<=",
        }[op]
        clausulas.append(f"{citado} {simbolo} ?")
        params.append(valor)
    if not clausulas:
        return "", params
    return " WHERE " + " AND ".join(clausulas), params


def _like(valor: str, op: str) -> str:
    escapado = valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    if op == "contem":
        return f"%{escapado}%"
    if op == "comeca_com":
        return f"{escapado}%"
    return f"%{escapado}"


def _order(ordenar: list[dict[str, str]] | None, tipos: dict[str, dict[str, Any]]) -> str:
    if not ordenar:
        return " ORDER BY " + citar("id") + " ASC"
    if len(ordenar) > 5:
        raise ErroConsulta(400, "Ordene por no máximo 5 colunas.")
    partes: list[str] = []
    for item in ordenar:
        coluna = item.get("coluna")
        direcao = item.get("direcao", "asc")
        if coluna not in tipos:
            raise ErroConsulta(400, f"Coluna desconhecida na ordenação: {coluna}.")
        if direcao not in {"asc", "desc"}:
            raise ErroConsulta(400, "Direção precisa ser asc ou desc.")
        partes.append(f"{citar(coluna)} {direcao.upper()}")
    return " ORDER BY " + ", ".join(partes)


def _serializar(row: sqlite3.Row, tipos: dict[str, dict[str, Any]]) -> dict[str, Any]:
    saida: dict[str, Any] = {}
    for coluna in row.keys():
        valor = row[coluna]
        tipo = tipos.get(coluna, {}).get("tipo")
        if tipo == "booleano" and valor is not None:
            valor = bool(valor)
        elif tipo == "decimal" and valor is not None:
            valor = float(valor)
        saida[coluna] = valor
    return saida


def _parametro_sql(valor: Any) -> Any:
    if isinstance(valor, bool):
        return int(valor)
    if valor is None or isinstance(valor, (str, int, float)):
        if isinstance(valor, float) and not math.isfinite(valor):
            raise ErroConsulta(400, "Parâmetro numérico inválido.")
        if isinstance(valor, str) and len(valor) > 10_000:
            raise ErroConsulta(400, "Parâmetro de texto maior que 10000 caracteres.")
        if isinstance(valor, int) and not isinstance(valor, bool) and abs(valor) > 2**63 - 1:
            raise ErroConsulta(400, "Parâmetro inteiro fora do intervalo.")
        return valor
    raise ErroConsulta(400, "Parâmetros do SQL aceitam texto, número, booleano ou nulo.")


def _limite(limite: int) -> int:
    if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= 500:
        raise ErroConsulta(400, "O limite fica entre 1 e 500.")
    return limite


def _deslocamento(deslocamento: int) -> int:
    if (
        not isinstance(deslocamento, int)
        or isinstance(deslocamento, bool)
        or deslocamento < 0
        or deslocamento > 100_000
    ):
        raise ErroConsulta(400, "O deslocamento fica entre 0 e 100000.")
    return deslocamento
