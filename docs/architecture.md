# Arquitetura

O pacote `datalink` separa contrato, transformação, validação, infraestrutura e orquestração. A transformação não abre rede nem arquivo. O `main` só carrega a configuração e dispara o pipeline.

```text
CSV  →  ingestion  →  validation  →  raw
raw  →  validation  →  transformations  →  refined
refined  →  transformations  →  marts  →  painel
```

A publicação passa pelo cliente HTTP. O pipeline não abre `data/banco.db` por conta própria.

| Caminho | Responsabilidade |
| --- | --- |
| `config/` | `BANCO_URL`, `BANCO_CAMINHO`, `BANCO_SEM_EXEMPLO`, porta 8741 |
| `domain/` | Contratos das três camadas e o protocolo do banco |
| `ingestion/` | Leitura dos CSVs e carga raw |
| `validation/` | Schema, nulos, duplicidade, nomes e SELECT |
| `transformations/` | JOIN, tipagem e indicadores, sem rede |
| `pipelines/` | Ordem raw, refined, marts e log de volumes |
| `infrastructure/` | SQLite, rotas FastAPI e cliente HTTP |
| `dashboard/` | Painel Streamlit, somente leitura das marts |

## Fontes e destinos

Fontes, na pasta `dados/bruto/`:

| Arquivo | Colunas |
| --- | --- |
| `clientes.csv` | `cliente_id`, `nome`, `cidade`, `estado` |
| `pedidos.csv` | `pedido_id`, `cliente_id`, `livro`, `valor`, `data_pedido` |

Destino operacional: SQLite local, por padrão `data/banco.db`. A API escuta em `127.0.0.1:8741`.

| Camada | Tabela | Conteúdo |
| --- | --- | --- |
| raw | `raw_clientes`, `raw_pedidos` | CSV como chegou. `valor` permanece texto |
| refined | `refined_pedidos` | Pedido com `cliente_nome`, `cidade`, `estado` e `valor` decimal |
| marts | `marts_resumo` | `qtd_pedidos`, `qtd_clientes`, `receita_total`, `ticket_medio` |
| marts | `marts_vendas_cidade` | Quantidade, receita e ticket médio por cidade e estado |
| marts | `marts_pedidos_cliente` | Quantidade, receita e ticket médio por cliente |
| marts | `marts_livros_cliente` | Um livro comprado por linha |

Cada carga apaga a tabela da camada e grava de novo. A mesma entrada produz o mesmo conteúdo lógico.

## Regras

- Chave de cliente: `cliente_id`. Chave de pedido: `pedido_id`. A primeira ocorrência fica; a seguinte é rejeitada.
- Campo obrigatório nulo ou vazio não avança. Espaço que não é o único conteúdo do texto permanece na raw e é removido na refined.
- Estado vai para maiúsculas na refined. `valor` só vira decimal nessa camada.
- Pedido sem cliente correspondente é rejeitado, com `pedido_id` e motivo, e não entra em `refined_pedidos`.
- `POST /sql` aceita apenas `SELECT`. Nome dinâmico de tabela sai de identificador validado. Valor externo entra por parâmetro.

!!! note

    Não há tabela nova de rejeição. O motivo, a contagem e o identificador saem no log da etapa e no retorno da carga.

## Rotas

| Rota | Uso |
| --- | --- |
| `GET /saude` | API no ar |
| `GET/POST /tabelas` | Lista ou cria tabela |
| `GET/DELETE /tabelas/{nome}` | Esquema ou remoção |
| `/tabelas/{nome}/linhas` | Inclui, lista, altera e apaga linhas |
| `POST /consulta` | Filtro, ordem e colunas |
| `POST /sql` | `SELECT` somente leitura |
| `GET /docs` | Documentação interativa da API |

Na subida, a coleção `livros` é semeada quando `BANCO_SEM_EXEMPLO` não é `1`.
