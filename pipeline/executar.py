"""Orquestra raw → refined → marts no Banco Local."""

from __future__ import annotations

from cliente import Banco, ErroBanco

from pipeline.marts import carregar_marts
from pipeline.raw import carregar_raw
from pipeline.refined import carregar_refined


def main() -> None:
    with Banco() as banco:
        bruto = carregar_raw(banco)
        print(f"raw: {bruto}")
        refinado = carregar_refined(banco)
        print(f"refined: {refinado}")
        indicadores = carregar_marts(banco)
        print(f"marts: {indicadores}")


if __name__ == "__main__":
    try:
        main()
    except ErroBanco as exc:
        raise SystemExit(str(exc)) from exc
