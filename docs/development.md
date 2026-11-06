# Desenvolvimento

Os comandos rodam na raiz do repositório. A virtualenv fica em `.venv`.

## Instalação

É preciso o pyenv com a versão de `.python-version` (linha 3.12) e o Poetry 2.

```powershell
pyenv local 3.12.10
poetry config virtualenvs.in-project true --local
poetry env use (pyenv which python)
poetry install
```

`requires-python` aceita `>=3.12,<3.13`. Dependência nova entra com `poetry add` ou `poetry add --group dev`.

## Execução

Suba a API:

```powershell
poetry run uvicorn datalink.infrastructure.api:app --host 127.0.0.1 --port 8741
```

Com a API no ar, carregue as três camadas:

```powershell
poetry run python -m datalink
```

Etapas separadas, nesta ordem:

```powershell
poetry run python -m datalink.pipelines.raw
poetry run python -m datalink.pipelines.refined
poetry run python -m datalink.pipelines.marts
```

Painel:

```powershell
poetry run streamlit run src/datalink/dashboard/painel.py
```

O painel abre em `http://localhost:8501`.

Variáveis lidas do ambiente:

| Variável | Papel |
| --- | --- |
| `BANCO_URL` | Endereço da API. Padrão `http://127.0.0.1:8741` |
| `BANCO_CAMINHO` | Arquivo SQLite. Padrão `data/banco.db` |
| `BANCO_SEM_EXEMPLO` | `1` impede a semeadura da coleção `livros` |
| `BANCO_SQL_SEGUNDOS` | Teto do `SELECT`. Padrão `2` |

Os nomes, sem valor, estão em `.env.example`.

## Testes

```powershell
poetry run pytest --cov=datalink --cov-report=term-missing --cov-fail-under=50
```

`poetry run pytest` já aplica esse piso. A cobertura mede o pacote `datalink`, não `tests/`. O gate roda `tests/unit`. Teste de pipeline não abre `data/banco.db` e não usa rede.

A suíte de integração fica de fora desse comando:

```powershell
poetry run pytest tests/integration -m integration --cov-fail-under=0
```

## Lint e documentação

```powershell
poetry run ruff check src tests
poetry run ruff format --check src tests
poetry run ruff check --select I src tests
poetry run task docs
poetry run mkdocs build --strict
```

`poetry run task docs` sobe o site MkDocs Material em `http://127.0.0.1:8000`. `mkdocs build --strict` é a validação de CI. O diretório `site/` não é versionado.

## Troubleshooting

- **Não conectou em 127.0.0.1:8741.** A API não está no ar. Suba o Uvicorn antes do pipeline e do painel.
- **Marts vazias ou painel sem indicador.** Rode `poetry run python -m datalink` com a API ligada. A ordem é raw, refined, marts.
- **Coleção `livros` ausente.** `BANCO_SEM_EXEMPLO=1` impede a semeadura. Apague a variável e suba a API de novo em um banco novo.
- **CSV não encontrado.** O pipeline lê `dados/bruto` a partir do diretório de trabalho. Execute na raiz do repositório.
- **Pedido sumiu da refined.** Cliente inexistente, chave duplicada, nulo obrigatório ou `valor` que não é decimal. O log da etapa traz identificador e motivo.
