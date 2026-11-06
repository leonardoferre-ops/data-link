"""Schema, nulos, duplicidade e pedido sem cliente."""

from __future__ import annotations

import math
import re
from typing import Any

from datalink.domain.contratos import Campo, LoteValidado, Rejeicao
from datalink.validation.nomes import COLUNAS_SISTEMA

TAMANHO_TEXTO = 10_000
LIMITE_INTEIRO = 2**63 - 1
_INTEIRO = re.compile(r"[+-]?\d+")


def sem_envelope(linha: dict[str, Any]) -> dict[str, Any]:
    """Remove id e criado_em acrescentados pela API."""
    return {
        chave: valor for chave, valor in linha.items() if chave not in COLUNAS_SISTEMA
    }


def validar_lote(
    linhas: list[dict[str, Any]],
    campos: tuple[Campo, ...],
    *,
    chaves: tuple[str, ...],
) -> LoteValidado:
    """Valida schema, tipo, nulo e duplicidade. A primeira chave permanece."""
    aceitos: list[dict[str, Any]] = []
    rejeitados: list[Rejeicao] = []
    vistos: set[tuple[Any, ...]] = set()
    for indice, linha in enumerate(linhas):
        identificador = _identificador(linha, chaves, indice)
        motivo, convertido = _conferir_registro(linha, campos)
        if motivo is not None:
            rejeitados.append(Rejeicao(identificador, motivo))
            continue
        if _duplicado(convertido, chaves, vistos):
            rejeitados.append(Rejeicao(identificador, _motivo_duplicado(chaves)))
            continue
        aceitos.append(convertido)
    return LoteValidado(tuple(aceitos), tuple(rejeitados))


def rejeitar_pedidos_sem_cliente(
    pedidos: list[dict[str, Any]],
    clientes: list[dict[str, Any]],
) -> LoteValidado:
    """Separa pedidos cujo cliente_id não existe na lista de clientes."""
    indice = _indexar_clientes(clientes)
    aceitos: list[dict[str, Any]] = []
    rejeitados: list[Rejeicao] = []
    for pedido in pedidos:
        motivo = _motivo_orfao(pedido, indice)
        if motivo is None:
            aceitos.append(pedido)
            continue
        rejeitados.append(Rejeicao(str(pedido.get("pedido_id", "?")), motivo))
    return LoteValidado(tuple(aceitos), tuple(rejeitados))


def _duplicado(
    linha: dict[str, Any],
    chaves: tuple[str, ...],
    vistos: set[tuple[Any, ...]],
) -> bool:
    if not chaves:
        return False
    marca = tuple(linha[nome] for nome in chaves)
    if marca in vistos:
        return True
    vistos.add(marca)
    return False


def _motivo_duplicado(chaves: tuple[str, ...]) -> str:
    return "Chave duplicada: " + ", ".join(chaves) + "."


def _identificador(linha: Any, chaves: tuple[str, ...], indice: int) -> str:
    if not isinstance(linha, dict):
        return f"linha-{indice}"
    partes = [
        str(linha[chave]).strip()
        for chave in chaves
        if chave in linha and linha[chave] not in (None, "")
    ]
    if partes:
        return ":".join(partes)
    return f"linha-{indice}"


def _conferir_registro(
    linha: Any,
    campos: tuple[Campo, ...],
) -> tuple[str | None, dict[str, Any]]:
    if not isinstance(linha, dict):
        return "Cada linha precisa ser um objeto.", {}
    conhecidos = {campo.nome: campo for campo in campos}
    extras = [nome for nome in linha if nome not in conhecidos]
    if extras:
        return "Colunas desconhecidas: " + ", ".join(extras) + ".", {}
    faltando = [
        campo.nome for campo in campos if campo.obrigatorio and campo.nome not in linha
    ]
    if faltando:
        return "Colunas obrigatórias ausentes: " + ", ".join(faltando) + ".", {}
    return _coagir_campos(linha, campos)


def _coagir_campos(
    linha: dict[str, Any],
    campos: tuple[Campo, ...],
) -> tuple[str | None, dict[str, Any]]:
    convertido: dict[str, Any] = {}
    for campo in campos:
        if campo.nome not in linha:
            continue
        try:
            convertido[campo.nome] = coagir(campo, linha[campo.nome])
        except ValueError as exc:
            return str(exc), {}
    return None, convertido


def coagir(campo: Campo, valor: Any) -> Any:
    """Converte o valor para o tipo do campo ou recusa nulo obrigatório."""
    if _nulo(valor):
        if campo.obrigatorio:
            raise ValueError(f"Valor nulo na coluna obrigatória {campo.nome}.")
        return None
    if campo.tipo == "texto":
        return _texto(campo.nome, valor)
    if campo.tipo == "inteiro":
        return _inteiro(campo.nome, valor)
    if campo.tipo == "decimal":
        return _decimal(campo.nome, valor)
    raise ValueError(f"Tipo desconhecido na coluna {campo.nome}.")


def _nulo(valor: Any) -> bool:
    if valor is None:
        return True
    return isinstance(valor, str) and valor.strip() == ""


def _texto(nome: str, valor: Any) -> str:
    if not isinstance(valor, str):
        raise ValueError(f"Valor de texto inválido na coluna {nome}.")
    if len(valor) > TAMANHO_TEXTO:
        raise ValueError(
            f"Texto maior que {TAMANHO_TEXTO} caracteres na coluna {nome}."
        )
    return valor


def _inteiro(nome: str, valor: Any) -> int:
    if isinstance(valor, bool):
        raise ValueError(f"Valor inteiro inválido na coluna {nome}.")
    numero = _ler_inteiro(nome, valor)
    if abs(numero) > LIMITE_INTEIRO:
        raise ValueError(f"Inteiro fora do intervalo na coluna {nome}.")
    return numero


def _ler_inteiro(nome: str, valor: Any) -> int:
    if isinstance(valor, int):
        return valor
    if isinstance(valor, str) and _INTEIRO.fullmatch(valor.strip()):
        return int(valor)
    raise ValueError(f"Valor inteiro inválido na coluna {nome}.")


def _decimal(nome: str, valor: Any) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
        raise ValueError(f"Valor decimal inválido na coluna {nome}.")
    try:
        numero = float(valor)
    except ValueError as exc:
        raise ValueError(f"Valor decimal inválido na coluna {nome}.") from exc
    if not math.isfinite(numero):
        raise ValueError(f"Valor decimal inválido na coluna {nome}.")
    return numero


def _indexar_clientes(clientes: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    indice: dict[int, dict[str, Any]] = {}
    for cliente in clientes:
        try:
            indice[int(cliente["cliente_id"])] = cliente
        except (KeyError, TypeError, ValueError):
            continue
    return indice


def _motivo_orfao(
    pedido: dict[str, Any], indice: dict[int, dict[str, Any]]
) -> str | None:
    try:
        cliente_id = int(pedido["cliente_id"])
    except (KeyError, TypeError, ValueError):
        return "cliente_id inválido."
    if cliente_id not in indice:
        return "Pedido sem cliente correspondente."
    return None
