"""Modelos de entrada da API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from datalink.domain.erros import ErroConsulta
from datalink.validation.nomes import OPERADORES, validar_nome, validar_nome_coluna


def _nome_tabela(valor: str) -> str:
    try:
        return validar_nome(valor, o_que="Tabela")
    except ErroConsulta as exc:
        raise ValueError(exc.mensagem) from exc


def _nome_coluna(valor: str) -> str:
    try:
        return validar_nome_coluna(valor)
    except ErroConsulta as exc:
        raise ValueError(exc.mensagem) from exc


class ColunaIn(BaseModel):
    """Coluna enviada na criação de uma tabela."""

    model_config = ConfigDict(extra="forbid")
    nome: str
    tipo: Literal["texto", "inteiro", "decimal", "booleano"]
    obrigatorio: bool = False

    @field_validator("nome")
    @classmethod
    def checar_nome(cls, valor: str) -> str:
        """Recusa nome de coluna inválido ou reservado."""
        return _nome_coluna(valor)


class TabelaIn(BaseModel):
    """Corpo de criação de tabela."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "nome": "contatos",
                    "colunas": [
                        {"nome": "nome", "tipo": "texto", "obrigatorio": True},
                        {"nome": "cidade", "tipo": "texto"},
                        {"nome": "ativo", "tipo": "booleano", "obrigatorio": True},
                    ],
                }
            ]
        },
    )
    nome: str
    colunas: list[ColunaIn] = Field(min_length=1, max_length=32)

    @field_validator("nome")
    @classmethod
    def checar_nome(cls, valor: str) -> str:
        """Recusa nome de tabela inválido."""
        return _nome_tabela(valor)


class LinhasIn(BaseModel):
    """Lote de linhas a inserir."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"linhas": [{"nome": "Ana Lima", "cidade": "Recife", "ativo": True}]}
            ]
        },
    )
    linhas: list[dict[str, Any]] = Field(min_length=1, max_length=200)


class AtualizarIn(BaseModel):
    """Colunas alteradas em uma linha existente."""

    model_config = ConfigDict(extra="forbid")
    valores: dict[str, Any] = Field(min_length=1)


class FiltroIn(BaseModel):
    """Filtro de uma consulta estruturada."""

    model_config = ConfigDict(extra="forbid")
    coluna: str
    op: Literal[
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
    ] = "igual"
    valor: Any = None

    @field_validator("op")
    @classmethod
    def checar_op(cls, valor: str) -> str:
        """Recusa operador fora da lista fechada."""
        if valor not in OPERADORES:
            raise ValueError("Operador de filtro inválido.")
        return valor


class OrdemIn(BaseModel):
    """Ordenação de uma consulta estruturada."""

    model_config = ConfigDict(extra="forbid")
    coluna: str
    direcao: Literal["asc", "desc"] = "asc"


class ConsultaIn(BaseModel):
    """Corpo de POST /consulta."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "tabela": "livros",
                    "filtros": [
                        {"coluna": "preco", "op": "menor", "valor": 40},
                        {"coluna": "genero", "op": "igual", "valor": "romance"},
                    ],
                    "ordenar": [{"coluna": "ano", "direcao": "asc"}],
                    "limite": 20,
                }
            ]
        },
    )
    tabela: str
    colunas: list[str] | None = None
    filtros: list[FiltroIn] = Field(default_factory=list)
    ordenar: list[OrdemIn] = Field(default_factory=list)
    limite: int = Field(50, ge=1, le=500)
    deslocamento: int = Field(0, ge=0, le=100_000)

    @field_validator("tabela")
    @classmethod
    def checar_tabela(cls, valor: str) -> str:
        """Recusa nome de tabela inválido."""
        return _nome_tabela(valor)


class SqlIn(BaseModel):
    """Corpo de POST /sql."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "sql": (
                        "SELECT autor, COUNT(*) AS quantidade FROM livros "
                        "GROUP BY autor ORDER BY quantidade DESC"
                    ),
                    "parametros": [],
                }
            ]
        },
    )
    sql: str = Field(min_length=1, max_length=5000)
    parametros: list[Any] = Field(default_factory=list, max_length=50)
