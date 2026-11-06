# Data Link

API local (SQLite) + pipeline em três camadas (`raw` → `refined` → `marts`) + painel Streamlit de indicadores.

A documentação completa está em [docs/index.md](docs/index.md).

## Visão geral

```text
dados/bruto/*.csv  →  raw_*  →  refined_*  →  marts_*  →  dashboard
```

| Camada | Tabelas | Papel |
| --- | --- | --- |
| **raw** | `raw_clientes`, `raw_pedidos` | CSVs sem alteração do texto de negócio |
| **refined** | `refined_pedidos` | JOIN `pedido.cliente_id = cliente.cliente_id` + tipagem |
| **marts** | `marts_resumo`, `marts_vendas_cidade`, `marts_pedidos_cliente`, `marts_livros_cliente` | Indicadores prontos para o painel |

O dashboard lê **somente** a camada marts. Nenhum cálculo acontece na tela.

## Pré-requisitos

- [pyenv](https://github.com/pyenv-win/pyenv-win) com o Python de `.python-version`
- [Poetry](https://python-poetry.org/) 2

## Setup

Na raiz do repositório:

```powershell
pyenv local 3.12.10
poetry config virtualenvs.in-project true --local
poetry env use (pyenv which python)
poetry install
```

## Subir a API

```powershell
poetry run uvicorn datalink.infrastructure.api:app --host 127.0.0.1 --port 8741
```

- Docs: http://127.0.0.1:8741/docs
- Saúde: http://127.0.0.1:8741/saude

Variáveis: `BANCO_CAMINHO`, `BANCO_SEM_EXEMPLO=1`, `BANCO_URL`. Os nomes estão em `.env.example`.

## Pipeline

Com a API no ar, ainda na raiz:

```powershell
poetry run python -m datalink
```

Etapa a etapa: `poetry run python -m datalink.pipelines.raw`, `poetry run python -m datalink.pipelines.refined`, `poetry run python -m datalink.pipelines.marts`.

Fontes brutas: `dados/bruto/clientes.csv` e `dados/bruto/pedidos.csv`.

## Painel

```powershell
poetry run streamlit run src/datalink/dashboard/painel.py
```

Abre em http://localhost:8501. Exibe resumo, pedidos por cliente, livros comprados e vendas por cidade. Se as marts não existirem, rode o pipeline antes.

## Testes e documentação

```powershell
poetry run pytest
poetry run ruff check src tests
poetry run ruff format --check src tests
poetry run mkdocs build --strict
```

Os testes do pipeline não abrem `data/banco.db`.

## Consultar com Python

```python
from datalink.infrastructure.cliente import Banco

with Banco("http://127.0.0.1:8741") as banco:
    por_cliente = banco.listar("marts_pedidos_cliente", ordenar="cliente_nome")
    for linha in por_cliente["linhas"]:
        print(linha["cliente_nome"], linha["qtd_pedidos"], linha["receita_total"])
```

SQL somente leitura em `/sql`.
