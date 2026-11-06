"""Contratos das camadas raw, refined e marts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Campo:
    """Coluna de um contrato: nome, tipo e obrigatoriedade."""

    nome: str
    tipo: str
    obrigatorio: bool = True


@dataclass(frozen=True)
class Rejeicao:
    """Registro barrado, com identificador e motivo."""

    identificador: str
    motivo: str


@dataclass(frozen=True)
class LoteValidado:
    """Linhas aceitas e rejeitadas de um lote."""

    aceitos: tuple[dict[str, Any], ...]
    rejeitados: tuple[Rejeicao, ...]


@dataclass(frozen=True)
class Carga:
    """Volumes publicados, contagens e rejeições de uma etapa."""

    volumes: dict[str, int]
    rejeitados: tuple[Rejeicao, ...]
    lidos: int
    aceitos: int


def colunas_api(campos: tuple[Campo, ...]) -> list[dict[str, Any]]:
    """Converte o contrato no corpo aceito por `POST /tabelas`."""
    return [
        {
            "nome": campo.nome,
            "tipo": campo.tipo,
            "obrigatorio": campo.obrigatorio,
        }
        for campo in campos
    ]


CAMPOS_CLIENTES_RAW: tuple[Campo, ...] = (
    Campo("cliente_id", "inteiro"),
    Campo("nome", "texto"),
    Campo("cidade", "texto"),
    Campo("estado", "texto"),
)

CAMPOS_PEDIDOS_RAW: tuple[Campo, ...] = (
    Campo("pedido_id", "inteiro"),
    Campo("cliente_id", "inteiro"),
    Campo("livro", "texto"),
    Campo("valor", "texto"),
    Campo("data_pedido", "texto"),
)

CAMPOS_PEDIDOS_REFINED: tuple[Campo, ...] = (
    Campo("pedido_id", "inteiro"),
    Campo("cliente_id", "inteiro"),
    Campo("cliente_nome", "texto"),
    Campo("cidade", "texto"),
    Campo("estado", "texto"),
    Campo("livro", "texto"),
    Campo("valor", "decimal"),
    Campo("data_pedido", "texto"),
)

CAMPOS_RESUMO: tuple[Campo, ...] = (
    Campo("indicador", "texto"),
    Campo("valor", "decimal"),
)

CAMPOS_VENDAS_CIDADE: tuple[Campo, ...] = (
    Campo("cidade", "texto"),
    Campo("estado", "texto"),
    Campo("qtd_pedidos", "inteiro"),
    Campo("receita_total", "decimal"),
    Campo("ticket_medio", "decimal"),
)

CAMPOS_PEDIDOS_CLIENTE: tuple[Campo, ...] = (
    Campo("cliente_id", "inteiro"),
    Campo("cliente_nome", "texto"),
    Campo("cidade", "texto"),
    Campo("estado", "texto"),
    Campo("qtd_pedidos", "inteiro"),
    Campo("receita_total", "decimal"),
    Campo("ticket_medio", "decimal"),
)

CAMPOS_LIVROS_CLIENTE: tuple[Campo, ...] = (
    Campo("pedido_id", "inteiro"),
    Campo("cliente_id", "inteiro"),
    Campo("cliente_nome", "texto"),
    Campo("livro", "texto"),
    Campo("valor", "decimal"),
    Campo("data_pedido", "texto"),
)

CAMPOS_MARTS: dict[str, tuple[Campo, ...]] = {
    "marts_resumo": CAMPOS_RESUMO,
    "marts_vendas_cidade": CAMPOS_VENDAS_CIDADE,
    "marts_pedidos_cliente": CAMPOS_PEDIDOS_CLIENTE,
    "marts_livros_cliente": CAMPOS_LIVROS_CLIENTE,
}
