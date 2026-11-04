# Data Link

API local (SQLite) + pipeline em três camadas + painel de indicadores.

## Camadas

| Camada | Tabelas | Papel |
| --- | --- | --- |
| **raw** | `raw_clientes`, `raw_pedidos` | Dado bruto dos CSVs, sem alteração de valores |
| **refined** | `refined_pedidos` | JOIN `pedido.cliente_id = cliente.cliente_id` + tipagem |
| **marts** | `marts_resumo`, `marts_vendas_cidade` | Indicadores prontos para o painel |

`raw_pedidos.cliente_id` liga as duas tabelas brutas. O dashboard lê **somente** marts.

## Subir a API

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8741
```

- Docs: http://127.0.0.1:8741/docs
- Saúde: http://127.0.0.1:8741/saude

## Rodar o pipeline

Com a API no ar:

```bash
python -m pipeline.executar
```

Ou etapa a etapa: `python -m pipeline.raw`, `python -m pipeline.refined`, `python -m pipeline.marts`.

## Painel

```bash
streamlit run dashboard/painel.py
```

O painel só exibe `marts_resumo` e `marts_vendas_cidade` — nenhum cálculo na tela.

## Testes

```bash
pytest
```

Os testes do pipeline (`testes/test_pipeline.py`) usam dados inventados em memória e **não** abrem `data/banco.db`.

## Consultar com Python

```python
from cliente import Banco

with Banco("http://127.0.0.1:8741") as banco:
    resultado = banco.consultar(
        "livros",
        colunas=["titulo", "autor", "ano", "preco"],
        filtros=[
            {"coluna": "preco", "op": "menor", "valor": 40},
            {"coluna": "autor", "op": "contem", "valor": "Amado"},
        ],
        ordenar=[{"coluna": "ano", "direcao": "asc"}],
    )
    for livro in resultado["linhas"]:
        print(livro["titulo"], livro["preco"])
```

SQL somente leitura em `/sql`. Variáveis: `BANCO_CAMINHO`, `BANCO_SEM_EXEMPLO=1`, `BANCO_URL`.
