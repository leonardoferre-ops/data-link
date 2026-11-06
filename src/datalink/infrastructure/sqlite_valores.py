"""Conversão e conferência dos valores gravados pela API."""

from __future__ import annotations

import math
from typing import Any

from datalink.domain.erros import ErroConsulta

TAMANHO_TEXTO = 10_000
LIMITE_INTEIRO = 2**63 - 1
LIMITE_COLUNAS = 32
LIMITE_LINHAS = 500
LIMITE_DESLOCAMENTO = 100_000


def conferir_linha(
    tipos: dict[str, dict[str, Any]],
    valores: dict[str, Any],
    *,
    parcial: bool,
) -> dict[str, Any]:
    """Confere colunas conhecidas, obrigatórias e tipos antes de gravar."""
    if not isinstance(valores, dict):
        raise ErroConsulta(400, "Cada linha precisa ser um objeto JSON.")
    desconhecidas = [coluna for coluna in valores if coluna not in tipos]
    if desconhecidas:
        raise ErroConsulta(
            400, "Colunas desconhecidas: " + ", ".join(desconhecidas) + "."
        )
    _exigir_conteudo(tipos, valores, parcial=parcial)
    saida = _converter_informadas(tipos, valores, parcial=parcial)
    if not parcial:
        _exigir_obrigatorias(tipos, valores)
    return saida


def converter(tipo: str, valor: Any, *, obrigatorio: bool, texto: bool = False) -> Any:
    """Converte um valor de coluna, com leitura opcional a partir de texto de URL."""
    if texto and isinstance(valor, str):
        valor = _coagir_texto(tipo, valor)
    if valor is None:
        if obrigatorio:
            raise ErroConsulta(400, "Coluna obrigatória não aceita nulo.")
        return None
    return _converter_presente(tipo, valor)


def colunas_select(
    pedidas: list[str] | None,
    tipos: dict[str, dict[str, Any]],
) -> list[str]:
    """Resolve as colunas do SELECT, recusando nome desconhecido."""
    if not pedidas:
        return list(tipos)
    if len(pedidas) > LIMITE_COLUNAS:
        raise ErroConsulta(400, "Selecione no máximo 32 colunas.")
    saida: list[str] = []
    for nome in pedidas:
        if nome not in tipos:
            raise ErroConsulta(400, f"Coluna desconhecida: {nome}.")
        if nome not in saida:
            saida.append(nome)
    return saida


def serializar(row: Any, tipos: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Converte uma linha do SQLite nos tipos expostos pela API."""
    saida: dict[str, Any] = {}
    # Row é iterável de valores; keys() é que devolve os nomes das colunas.
    for coluna in row.keys():  # noqa: SIM118
        valor = row[coluna]
        tipo = tipos.get(coluna, {}).get("tipo")
        saida[coluna] = _valor_serializado(tipo, valor)
    return saida


def parametro_sql(valor: Any) -> Any:
    """Aceita texto, número, booleano ou nulo como parâmetro de SELECT."""
    if isinstance(valor, bool):
        return int(valor)
    if valor is None or isinstance(valor, (str, int, float)):
        _recusar_parametro_invalido(valor)
        return valor
    raise ErroConsulta(
        400, "Parâmetros do SQL aceitam texto, número, booleano ou nulo."
    )


def limite_linhas(limite: int) -> int:
    """Garante limite entre 1 e 500."""
    if (
        not isinstance(limite, int)
        or isinstance(limite, bool)
        or not 1 <= limite <= LIMITE_LINHAS
    ):
        raise ErroConsulta(400, "O limite fica entre 1 e 500.")
    return limite


def deslocamento_linhas(deslocamento: int) -> int:
    """Garante deslocamento entre 0 e 100000."""
    if (
        not isinstance(deslocamento, int)
        or isinstance(deslocamento, bool)
        or deslocamento < 0
        or deslocamento > LIMITE_DESLOCAMENTO
    ):
        raise ErroConsulta(400, "O deslocamento fica entre 0 e 100000.")
    return deslocamento


def _exigir_conteudo(
    tipos: dict[str, dict[str, Any]],
    valores: dict[str, Any],
    *,
    parcial: bool,
) -> None:
    if (
        not parcial
        and not valores
        and any(info["obrigatorio"] for info in tipos.values())
    ):
        raise ErroConsulta(400, "Informe as colunas obrigatórias.")
    if parcial and not valores:
        raise ErroConsulta(400, "Informe ao menos uma coluna para atualizar.")


def _converter_informadas(
    tipos: dict[str, dict[str, Any]],
    valores: dict[str, Any],
    *,
    parcial: bool,
) -> dict[str, Any]:
    nomes = valores.keys() if parcial else [nome for nome in tipos if nome in valores]
    return {
        nome: converter(
            tipos[nome]["tipo"], valores[nome], obrigatorio=tipos[nome]["obrigatorio"]
        )
        for nome in nomes
    }


def _exigir_obrigatorias(
    tipos: dict[str, dict[str, Any]], valores: dict[str, Any]
) -> None:
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


def _converter_presente(tipo: str, valor: Any) -> Any:
    if tipo == "texto":
        return _texto(valor)
    if tipo == "inteiro":
        return _inteiro(valor)
    if tipo == "decimal":
        return _decimal(valor)
    if tipo == "booleano":
        return _booleano(valor)
    raise ErroConsulta(400, "Tipo de coluna desconhecido.")


def _texto(valor: Any) -> str:
    if not isinstance(valor, str):
        raise ErroConsulta(400, "Valor de texto inválido.")
    if len(valor) > TAMANHO_TEXTO:
        raise ErroConsulta(400, "Texto maior que 10000 caracteres.")
    return valor


def _inteiro(valor: Any) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ErroConsulta(400, "Valor inteiro inválido.")
    if abs(valor) > LIMITE_INTEIRO:
        raise ErroConsulta(400, "Inteiro fora do intervalo do SQLite.")
    return valor


def _decimal(valor: Any) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErroConsulta(400, "Valor decimal inválido.")
    numero = float(valor)
    if not math.isfinite(numero):
        raise ErroConsulta(400, "Valor decimal inválido.")
    return numero


def _booleano(valor: Any) -> bool:
    if not isinstance(valor, bool):
        raise ErroConsulta(400, "Valor booleano inválido. Use true ou false.")
    return valor


def _coagir_texto(tipo: str, valor: str) -> Any:
    if valor == "" or valor.lower() == "null":
        return None
    if tipo == "texto":
        return valor
    if tipo == "inteiro":
        return _inteiro_texto(valor)
    if tipo == "decimal":
        return _decimal_texto(valor)
    if tipo == "booleano":
        return _booleano_texto(valor)
    raise ErroConsulta(400, "Tipo de coluna desconhecido.")


def _inteiro_texto(valor: str) -> int:
    try:
        return int(valor)
    except ValueError as exc:
        raise ErroConsulta(400, f"Não foi possível ler o inteiro {valor!r}.") from exc


def _decimal_texto(valor: str) -> float:
    try:
        return float(valor)
    except ValueError as exc:
        raise ErroConsulta(400, f"Não foi possível ler o decimal {valor!r}.") from exc


def _booleano_texto(valor: str) -> bool:
    mapa = {"true": True, "false": False, "1": True, "0": False}
    if valor.lower() not in mapa:
        raise ErroConsulta(400, "Booleano na URL aceita true, false, 1 ou 0.")
    return mapa[valor.lower()]


def _valor_serializado(tipo: str | None, valor: Any) -> Any:
    if tipo == "booleano" and valor is not None:
        return bool(valor)
    if tipo == "decimal" and valor is not None:
        return float(valor)
    return valor


def _recusar_parametro_invalido(valor: Any) -> None:
    if isinstance(valor, float) and not math.isfinite(valor):
        raise ErroConsulta(400, "Parâmetro numérico inválido.")
    if isinstance(valor, str) and len(valor) > TAMANHO_TEXTO:
        raise ErroConsulta(400, "Parâmetro de texto maior que 10000 caracteres.")
    if (
        isinstance(valor, int)
        and not isinstance(valor, bool)
        and abs(valor) > LIMITE_INTEIRO
    ):
        raise ErroConsulta(400, "Parâmetro inteiro fora do intervalo.")
