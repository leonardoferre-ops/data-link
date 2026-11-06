# Data Link

API local em SQLite, pipeline medalhão e painel de indicadores de pedidos de livros. Tudo roda na máquina. Não há conta, chave nem deploy.

O fluxo parte de dois CSVs, grava as camadas pela API e deixa o painel só ler os indicadores prontos.

```text
dados/bruto/*.csv  →  raw_*  →  refined_*  →  marts_*  →  painel
```

## Por onde começar

1. Instale o ambiente como em [Desenvolvimento](development.md).
2. Suba a API em `http://127.0.0.1:8741`.
3. Rode `poetry run python -m datalink` na raiz do repositório.
4. Abra o painel em `http://localhost:8501`.

O desenho das camadas, os contratos e as rejeições estão em [Arquitetura](architecture.md).
