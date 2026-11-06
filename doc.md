# Data Link

API local em SQLite, pipeline em três camadas e painel Streamlit de indicadores de pedidos de livros. Tudo roda na máquina; não há conta, chave nem deploy.

## O que o projeto faz

1. A API (`Banco Local`) cria tabelas e grava linhas em `data/banco.db`.
2. O pipeline lê CSVs em `dados/bruto/`, sobe `raw` → `refined` → `marts` pela API.
3. O painel lê **somente** as tabelas marts. Nenhum cálculo acontece na tela.

```text
dados/bruto/*.csv  →  raw_*  →  refined_*  →  marts_*  →  dashboard
```

O cliente Python fala com a API em `http://127.0.0.1:8741` (variável `BANCO_URL`).

## Camadas

| Camada | Tabelas | O que entra |
| --- | --- | --- |
| **raw** | `raw_clientes`, `raw_pedidos` | CSV como está. `valor` permanece texto. |
| **refined** | `refined_pedidos` | JOIN `pedido.cliente_id = cliente.cliente_id`. Nome, cidade e livro sem espaços extras; estado em maiúsculas; `valor` vira decimal. Pedido sem cliente é rejeitado e não entra. |
| **marts** | `marts_resumo`, `marts_vendas_cidade`, `marts_pedidos_cliente`, `marts_livros_cliente` | Indicadores prontos: quantidade, receita e ticket médio (geral, por cidade e por cliente) e a lista de livros comprados. |

Fontes: `dados/bruto/clientes.csv` (`cliente_id`, `nome`, `cidade`, `estado`) e `dados/bruto/pedidos.csv` (`pedido_id`, `cliente_id`, `livro`, `valor`, `data_pedido`). Cada carga recria a tabela antes de inserir.

`marts_resumo` guarda quatro linhas: `qtd_pedidos`, `qtd_clientes`, `receita_total`, `ticket_medio`.

## API

FastAPI + SQLite. Sobe com:

```powershell
poetry run uvicorn datalink.infrastructure.api:app --host 127.0.0.1 --port 8741
```

| Rota | Uso |
| --- | --- |
| `GET /saude` | Confere se a API está no ar |
| `GET/POST /tabelas` | Lista ou cria tabela |
| `GET/DELETE /tabelas/{nome}` | Esquema ou remoção |
| `/tabelas/{nome}/linhas` | Inclui, lista, altera e apaga linhas |
| `POST /consulta` | Filtro, ordem e colunas sem escrever SQL |
| `POST /sql` | `SELECT` somente leitura |

Na subida, se `BANCO_SEM_EXEMPLO` não for `1`, a API semeia a coleção `livros`. O arquivo do banco pode mudar com `BANCO_CAMINHO`. Documentação interativa em `/docs`.

## Pipeline

A API precisa estar no ar. Os comandos rodam na raiz do repositório.

```powershell
poetry run python -m datalink
```

Etapas separadas, nesta ordem:

```powershell
poetry run python -m datalink.pipelines.raw
poetry run python -m datalink.pipelines.refined
poetry run python -m datalink.pipelines.marts
```

## Painel

```powershell
poetry run streamlit run src/datalink/dashboard/painel.py
```

Abre em http://localhost:8501 e mostra o resumo, pedidos por cliente (com filtro), livros comprados (com filtro) e vendas por cidade. Se as marts não existirem, rode o pipeline antes.

## Testes e registro de mudanças

```powershell
poetry run pytest
```

Os testes do pipeline usam dados em memória e não abrem `data/banco.db`.

Histórico em `logs/alteracoes.log`:

```powershell
poetry run python -m logs.registrar CHG "Descrição do que mudou"
```

Tipos: `ADD`, `CHG`, `FIX`, `DEL`, `DOCS`, `TEST`, `INIT`.

## Onde está cada parte

```text
src/datalink/config/          ambiente e limites
src/datalink/domain/          contratos e protocolo do banco
src/datalink/ingestion/       CSV para a camada raw
src/datalink/validation/      schema, nulos, duplicidade e pedido sem cliente
src/datalink/transformations/ JOIN, tipagem e indicadores
src/datalink/pipelines/       ordem raw, refined, marts e log
src/datalink/infrastructure/  SQLite, API e cliente HTTP
src/datalink/dashboard/       painel Streamlit, somente marts
dados/bruto/                  CSVs de origem
tests/                        pytest
logs/                         histórico de alterações
docs/                         documentação MkDocs
```

Instalação, arquitetura e execução estão em `docs/` e no `README.md`.
