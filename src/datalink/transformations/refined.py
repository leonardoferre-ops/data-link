"""Funções puras de conformação do pedido com o cliente."""

from __future__ import annotations

import math
from typing import Any


def conformar_pedido(pedido: dict[str, Any], cliente: dict[str, Any]) -> dict[str, Any]:
    """Une um pedido ao cliente e aplica a tipagem da camada refined."""
    return {
        "pedido_id": int(pedido["pedido_id"]),
        "cliente_id": int(pedido["cliente_id"]),
        "cliente_nome": str(cliente["nome"]).strip(),
        "cidade": str(cliente["cidade"]).strip(),
        "estado": str(cliente["estado"]).strip().upper(),
        "livro": str(pedido["livro"]).strip(),
        "valor": _decimal(pedido["valor"], pedido.get("pedido_id")),
        "data_pedido": str(pedido["data_pedido"]).strip(),
    }


def _decimal(valor: Any, pedido_id: Any) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
        raise ValueError(f"Valor inválido no pedido {pedido_id}.")
    try:
        numero = float(valor)
    except ValueError as exc:
        raise ValueError(f"Valor inválido no pedido {pedido_id}.") from exc
    if not math.isfinite(numero):
        raise ValueError(f"Valor inválido no pedido {pedido_id}.")
    return numero
