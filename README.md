# Data Link

API local (SQLite) + pipeline em três camadas (`raw` → `refined` → `marts`) + painel Streamlit de indicadores.

## Visão geral

```text
dados/bruto/*.csv  →  raw_*  →  refined_*  →  marts_*  →  dashboard
```

| Camada | Tabelas | Papel |
| --- | --- | --- |
| **raw** | `raw_clientes`, `raw_pedidos` | CSVs sem alteração de valores |
| **refined** | `refined_pedidos` | JOIN `pedido.cliente_id = cliente.cliente_id` + tipagem |
| **marts** | `marts_resumo`, `marts_vendas_cidade`, `marts_pedidos_cliente`, `marts_livros_cliente` | Indicadores prontos para o painel |

O dashboard lê **somente** a camada marts — nenhum cálculo na tela.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Use sempre o Python do `.venv` (ou `.\.venv\Scripts\python.exe`) para API, pipeline, testes e painel.

## Subir a API

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8741
```

- Docs: http://127.0.0.1:8741/docs  
- Saúde: http://127.0.0.1:8741/saude  

Variáveis: `BANCO_CAMINHO`, `BANCO_SEM_EXEMPLO=1`, `BANCO_URL`.

## Pipeline

Com a API no ar:

```powershell
python -m pipeline.executar
```

Etapa a etapa: `python -m pipeline.raw`, `python -m pipeline.refined`, `python -m pipeline.marts`.

Fontes brutas: `dados/bruto/clientes.csv` e `dados/bruto/pedidos.csv`.

## Painel

```powershell
python -m streamlit run dashboard/painel.py
```

Abre em http://localhost:8501. Exibe:

- resumo (`marts_resumo`)
- pedidos por cliente (`marts_pedidos_cliente`)
- livros comprados (`marts_livros_cliente`), com filtro por cliente
- vendas por cidade (`marts_vendas_cidade`)

Se as tabelas marts não existirem, rode `python -m pipeline.executar` antes.

## Testes

```powershell
python -m pytest
```

Os testes do pipeline (`testes/test_pipeline.py`) usam dados inventados em memória e **não** abrem `data/banco.db`.

## Logs de alterações

Histórico em [`logs/alteracoes.log`](logs/alteracoes.log). Registrar uma mudança:

```powershell
python -m logs.registrar ADD "Descrição do que mudou"
```

Tipos: `ADD`, `CHG`, `FIX`, `DEL`, `DOCS`, `TEST`, `INIT`.

## Estrutura

```text
app/                 API FastAPI + SQLite
cliente.py           Cliente HTTP do Banco Local
dados/bruto/         CSVs de origem
pipeline/            raw, refined, marts, executar
dashboard/painel.py  Streamlit (só marts)
testes/              pytest (API + pipeline)
logs/                histórico de alterações do projeto
```

## Consultar com Python

```python
from cliente import Banco

with Banco("http://127.0.0.1:8741") as banco:
    por_cliente = banco.listar("marts_pedidos_cliente", ordenar="cliente_nome")
    for linha in por_cliente["linhas"]:
        print(linha["cliente_nome"], linha["qtd_pedidos"], linha["receita_total"])
```

SQL somente leitura em `/sql`.
