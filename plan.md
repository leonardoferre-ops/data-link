# Plano de criação do Data Link

Plano oficial de criação do Data Link. O produto está em [doc.md](doc.md). O padrão de engenharia está em [SKILL.md](SKILL.md). Onde o skill diz `projeto`, leia-se o pacote `datalink`.

Nesta etapa só se grava este plano. Não se cria ambiente, código, MkDocs nem CI.

## Fontes

| Documento | Papel |
| --- | --- |
| [doc.md](doc.md) | O que o sistema faz: API SQLite local, pipeline `raw` → `refined` → `marts`, painel que só lê marts |
| [SKILL.md](SKILL.md) | Como construir: pyenv, Poetry, layout `src/`, Ruff, pytest com piso de 50%, MkDocs Material, pipelines idempotentes e CI |

## Situação atual

O repositório já entrega o comportamento do `doc.md`, fora do layout do skill:

- API FastAPI em `app/`, cliente HTTP em `cliente.py`, pipeline em `pipeline/`, painel em `dashboard/painel.py`, testes em `testes/`.
- Dependências em `requirements.txt` e `pyproject.toml`, instaladas com `pip`. Não há Poetry, `poetry.lock`, `.python-version` nem `src/`.
- Não há `mkdocs.yml`, `docs/` nem `.github/workflows/`.
- O banco é SQLite local (`data/banco.db`). Não há deploy.

A criação descrita aqui preserva esse comportamento e o recoloca no padrão do skill.

## Decisões

- Pacote importável: `datalink`, em `src/datalink/`.
- Execução só na máquina. Sem conta, chave, Spark, Airflow, Databricks ou deploy.
- Banco: SQLite. Caminho por `BANCO_CAMINHO`. Sem `DATABASE_URL` e sem Postgres.
- A API continua em `http://127.0.0.1:8741`. O cliente usa `BANCO_URL`.
- `BANCO_SEM_EXEMPLO=1` impede a semeadura da coleção `livros` na subida.
- Medalhão do domínio, com os nomes já usados no produto: raw (bruto), refined (conformado), marts (consumo). O painel não calcula.
- Cada carga recria a tabela da camada antes de inserir. A mesma entrada produz o mesmo conteúdo lógico.
- HTTP com `httpx`. API com FastAPI e Uvicorn. Painel com Streamlit. Dependências só pelo Poetry.
- Python alinhado entre `.python-version` e `requires-python`. Linha alvo: `>=3.12,<3.13`, salvo o pyenv local já instalado exigir outro patch da 3.12. Os dois arquivos descrevem a mesma linha.
- `logs/` permanece como histórico de alterações do repositório (`python -m logs.registrar`). Não entra na cobertura do pacote.

## Fluxo de dados

```mermaid
flowchart LR
  csv[CSVs_dados_bruto]
  raw[raw_clientes_e_raw_pedidos]
  refined[refined_pedidos]
  marts[marts]
  painel[Painel_Streamlit]
  csv --> raw --> refined --> marts --> painel
```

1. Ingerir `dados/bruto/clientes.csv` e `dados/bruto/pedidos.csv` e gravar a camada raw sem transformar o texto de negócio. `valor` do pedido permanece texto.
2. Validar chave e presença do cliente. Pedido sem `cliente_id` correspondente é rejeitado e não entra em `refined_pedidos`.
3. Conformar: JOIN `pedido.cliente_id = cliente.cliente_id`, nomes sem espaços extras, estado em maiúsculas, `valor` decimal.
4. Materializar os indicadores em marts. O painel só lista essas tabelas.
5. `main.py` carrega a configuração e chama o pipeline. Não filtra, não valida schema e não grava tabela.

A API precisa estar no ar antes do pipeline e do painel. O pipeline fala com ela pelo cliente HTTP, não abre o arquivo SQLite por conta própria.

## Contratos de dados

Fontes:

- Cliente: `cliente_id`, `nome`, `cidade`, `estado`
- Pedido: `pedido_id`, `cliente_id`, `livro`, `valor`, `data_pedido`

| Camada | Tabela | Conteúdo |
| --- | --- | --- |
| raw | `raw_clientes`, `raw_pedidos` | CSV como chegou, com `valor` em texto |
| refined | `refined_pedidos` | Pedido enriquecido com `cliente_nome`, `cidade`, `estado` e `valor` decimal |
| marts | `marts_resumo` | `qtd_pedidos`, `qtd_clientes`, `receita_total`, `ticket_medio` |
| marts | `marts_vendas_cidade` | Quantidade, receita e ticket médio por cidade e estado |
| marts | `marts_pedidos_cliente` | Quantidade, receita e ticket médio por cliente |
| marts | `marts_livros_cliente` | Um livro comprado por linha |

`POST /sql` aceita apenas `SELECT`. Nome dinâmico de tabela, quando existir, sai de lista fechada do código. Valor externo entra por parâmetro do driver.

## Estrutura a criar

Espelha o skill, só com o que este produto usa. O pacote `datalink` ocupa o lugar de `projeto`.

```text
data-link/
├── pyproject.toml
├── poetry.lock
├── poetry.toml
├── .python-version
├── .gitignore
├── README.md
├── doc.md
├── SKILL.md
├── plan.md
├── mkdocs.yml
├── dados/bruto/
├── src/datalink/
│   ├── __init__.py
│   ├── main.py
│   ├── config/            BANCO_URL, BANCO_CAMINHO, BANCO_SEM_EXEMPLO, porta 8741
│   ├── domain/            contratos das três camadas e Protocol do banco
│   ├── ingestion/         leitura dos CSVs e carga raw
│   ├── validation/        schema, nulos, duplicidade e pedido sem cliente
│   ├── transformations/   JOIN, tipagem e indicadores de marts
│   ├── pipelines/         orquestra raw, refined e marts
│   ├── infrastructure/    SQLite, API FastAPI e cliente HTTP
│   ├── dashboard/         painel Streamlit, somente leitura das marts
│   └── utils/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
└── docs/
    ├── index.md
    ├── architecture.md
    └── development.md
```

| Caminho novo | Origem atual | Responsabilidade |
| --- | --- | --- |
| `infrastructure/` | `app/`, `cliente.py` | SQLite, rotas e cliente HTTP. Sem regra de JOIN ou indicador |
| `ingestion/` | `pipeline/raw.py` | CSV para `raw_*` |
| `transformations/` | `pipeline/refined.py`, `pipeline/marts.py` | Funções puras, sem rede |
| `validation/` | regras hoje implícitas no refined | Rejeição explícita do pedido sem cliente |
| `pipelines/` | `pipeline/executar.py` | Ordem raw, refined, marts e log de volumes |
| `dashboard/` | `dashboard/painel.py` | Métricas, filtro de cliente e tabelas. Sem agregação nova |
| `config/` | variáveis lidas espalhadas | Um único lugar para ambiente |

Limites de import: os do [SKILL.md](SKILL.md). Transformação e validação não importam infraestrutura. `main.py` importa `config` e `pipelines`.

Rotas que permanecem:

| Rota | Uso |
| --- | --- |
| `GET /saude` | API no ar |
| `GET/POST /tabelas` | Lista ou cria tabela |
| `GET/DELETE /tabelas/{nome}` | Esquema ou remoção |
| `/tabelas/{nome}/linhas` | Inclui, lista, altera e apaga linhas |
| `POST /consulta` | Filtro, ordem e colunas |
| `POST /sql` | `SELECT` somente leitura |
| `GET /docs` | Documentação interativa da API |

Na subida, semear `livros` quando `BANCO_SEM_EXEMPLO` não for `1`.

## Ordem de implementação

1. Fixar o Python no pyenv e em `.python-version`. Criar a virtualenv do Poetry dentro do projeto (`poetry config virtualenvs.in-project true --local`) e apontá-la para esse interpretador.
2. Declarar dependências de produção (FastAPI, Uvicorn, httpx, Streamlit) com `poetry add`. Declarar Ruff, pytest, pytest-cov e MkDocs Material com `poetry add --group dev`. Versionar `poetry.lock`. Retirar `requirements.txt` do fluxo de instalação.
3. Copiar para o `pyproject.toml` a configuração de Ruff, pytest e cobertura do skill, com `known-first-party = ["datalink"]`, `source = ["datalink"]` e `--cov=datalink`.
4. Mover o código para `src/datalink/`, separando domínio, transformação pura, validação, infraestrutura e orquestração. Manter os contratos e o comportamento descritos acima.
5. Cobrir sucesso, entrada inválida, limite e exceção das transformações e da validação. Teste unitário não abre `data/banco.db` nem usa rede. O gate é `poetry run pytest --cov=datalink --cov-report=term-missing --cov-fail-under=50`.
6. Documentar instalação, arquitetura, fontes, destinos, contratos e execução em `docs/` e no `README.md`. Validar com `poetry run mkdocs build --strict`.
7. Fechar com Ruff (`check`, `format --check` e `--select I`) e acrescentar o workflow de CI sugerido no skill, trocando `projeto` por `datalink`.
8. Registrar neste plano o que ficou de fora.

Comandos de execução, depois da mudança:

```powershell
poetry run uvicorn datalink.infrastructure.api:app --host 127.0.0.1 --port 8741
poetry run python -m datalink
poetry run streamlit run src/datalink/dashboard/painel.py
```

O nome exato do módulo da API pode ajustar na implementação, desde que a porta, as rotas e as variáveis de ambiente permaneçam as do `doc.md`. Etapas separadas do pipeline continuam disponíveis e na mesma ordem: raw, refined, marts.

## Fora desta entrega

- Deploy da API, do banco ou do painel.
- Postgres, Render ou outro backend remoto.
- Spark, Airflow e Databricks.
- Novas fontes além dos dois CSVs e novas marts além das quatro tabelas do `doc.md`.
- Publicação do site MkDocs. O CI só executa `mkdocs build --strict`.

## Critério de aceite

A criação está aceita quando os critérios da seção 13 do [SKILL.md](SKILL.md) forem verdadeiros para o pacote `datalink` e o comportamento do [doc.md](doc.md) continuar verdadeiro:

1. Python local no pyenv e em `.python-version`, com a mesma linha em `requires-python`.
2. Dependências só no Poetry, virtualenv do projeto e `poetry.lock` versionado.
3. Layout `src/datalink/` com os limites de import do skill.
4. `poetry run ruff check src tests` sem erro.
5. `poetry run ruff format --check src tests` sem erro.
6. `poetry run ruff check --select I src tests` sem erro.
7. `poetry run pytest --cov=datalink --cov-report=term-missing --cov-fail-under=50` passando, medido sobre `datalink` e não sobre `tests/`.
8. `docs/` no MkDocs Material e `poetry run mkdocs build --strict` passando.
9. Sem segredo, dado real de produção ou dependência instalada no Python global.
10. Esses comandos executados de verdade, com o resultado informado. Lint, teste, cobertura ou documentação não se declaram prontos sem essa execução.

O produto, além do gate do skill, precisa disto:

- API em `127.0.0.1:8741` com as rotas do `doc.md` e `SELECT` somente leitura.
- Pipeline idempotente: raw sem alterar o texto de negócio, refined com JOIN e tipagem, marts com as quatro tabelas.
- Painel em `localhost:8501` lendo só marts, com resumo, pedidos por cliente, livros comprados e vendas por cidade.
- Teste de pipeline sem abrir `data/banco.db`.
