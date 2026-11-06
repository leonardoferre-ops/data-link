---
name: engenharia-dados-python
description: >-
  Padrão oficial de Engenharia de Dados Python: pyenv, Poetry, arquitetura
  src em camadas, Ruff, pytest com cobertura mínima de 50%, MkDocs Material,
  pipelines idempotentes, segurança e validação em CI. Use ao criar, alterar,
  revisar, testar ou documentar projetos Python de dados, pipelines, ingestão,
  transformação ou qualidade de dados.
---

# Skill — Engenharia de Dados Python

Padrão oficial do time para projetos Python de Engenharia de Dados. Desenvolvedores e agentes de IA usam este arquivo como referência ao criar, implementar, refatorar, testar e documentar código.

Onde este texto diz `projeto`, use o nome importável do pacote em `src/projeto`.

## Objetivo

Entregar pipelines e bibliotecas de dados reproduzíveis, modulares, testáveis e seguras, com o mesmo fluxo de ambiente, qualidade e documentação em todos os repositórios.

## Escopo de aplicação

Aplique esta skill em todo projeto Python do time, em especial quando o trabalho envolver:

- ambiente, versão do Python ou dependências;
- ingestão, transformação, validação ou disponibilização de dados;
- alteração de código em `src/` ou de testes em `tests/`;
- lint, formatação, cobertura ou documentação;
- revisão de pull request, pipeline de CI ou preparação para merge.

A skill define o padrão de engenharia. A escolha de motor de processamento, orquestrador ou plataforma (por exemplo Spark, Airflow ou Databricks) depende do volume, da latência e da operação do projeto. Essas ferramentas não são obrigatórias por padrão.

## Princípios fundamentais

1. A versão do Python e as dependências são explícitas e reproduzíveis.
2. Código de negócio, infraestrutura e orquestração ficam em módulos diferentes.
3. Transformações são funções pequenas, previsíveis e testáveis sem rede.
4. Pipelines são idempotentes: executá-los de novo com a mesma entrada produz o mesmo resultado lógico.
5. Credenciais, tokens e senhas ficam fora do código, dos logs e do Git.
6. Lint, teste, cobertura e documentação são critérios de aceite, não etapas opcionais.
7. Clareza vence solução engenhosa. Cada módulo tem uma razão para mudar.

## 1. Ambiente e dependências

O Poetry é a ferramenta oficial de dependências, virtualenv e execução. O pyenv define a versão local do Python. O `pyproject.toml` é o arquivo central de configuração. O `poetry.lock` é versionado.

A virtualenv pertence somente a este projeto. O Poetry deve criá-la dentro do repositório:

```bash
poetry config virtualenvs.in-project true --local
```

O comando gera `poetry.toml`:

```toml
[virtualenvs]
in-project = true
```

### Versão do Python

1. Escolha uma versão compatível com todas as dependências.
2. Instale-a no pyenv, se ainda não existir.
3. Fixe-a na raiz com `pyenv local 3.12.8` (use a versão real do projeto).
4. Confira `.python-version` e `pyenv version`. A versão exibida é a local do diretório.
5. Associe o Poetry a esse interpretador.

```bash
pyenv local 3.12.8
pyenv version
poetry env use "$(pyenv which python)"
poetry env info
```

No PowerShell:

```powershell
poetry env use (pyenv which python)
```

`requires-python` no `pyproject.toml` aceita a versão de `.python-version` e rejeita versões incompatíveis com as dependências. Ao mudar a versão, atualize os dois juntos e rode a suíte de testes.

No Windows, pyenv-win usa os mesmos comandos `pyenv local` e `pyenv which python`.

### Dependências

- Produção fica no grupo principal.
- Ruff, pytest, pytest-cov e MkDocs Material ficam no grupo `dev`.
- Inclusão, remoção e atualização passam pelos comandos do Poetry, para o `poetry.lock` permanecer sincronizado.
- Toda ferramenta do projeto roda com `poetry run`.

Comandos corretos:

```bash
poetry install
poetry add polars
poetry add --group dev ruff pytest pytest-cov mkdocs-material
poetry remove pacote-nao-usado
poetry lock
poetry run pytest
poetry run python -m projeto
```

Comandos incorretos:

```bash
pip install polars
pip install -r requirements.txt
python -m venv .venv && pip install -e .
poetry run pip install ruff
pipx install ruff
```

`requirements.txt` não é a fonte de dependências. Exportá-lo para uma ferramenta externa é exceção pontual, nunca o fluxo do time. Pacotes do projeto não são instalados no Python global.

Antes de implementar, confirme com `poetry env info` que o executável está em `.venv` e que o Python é o do `.python-version`.

## 2. Arquitetura e modularidade

O layout `src/` é obrigatório. A árvore abaixo é a referência. Mantenha apenas as pastas que o domínio exigir e crie outras quando uma responsabilidade nova não couber nas existentes.

```text
projeto/
├── pyproject.toml
├── poetry.lock
├── poetry.toml
├── .python-version
├── .gitignore
├── README.md
├── mkdocs.yml
├── src/
│   └── projeto/
│       ├── __init__.py
│       ├── main.py
│       ├── config/
│       ├── core/
│       ├── domain/
│       ├── pipelines/
│       ├── ingestion/
│       ├── transformations/
│       ├── validation/
│       ├── infrastructure/
│       └── utils/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
└── docs/
    ├── index.md
    ├── architecture.md
    └── development.md
```

| Caminho | Responsabilidade |
| --- | --- |
| `domain/` | Entidades, enums, regras de negócio e contratos (Protocol). Sem I/O. |
| `core/` | Serviços de aplicação que coordenam o domínio sem conhecer o driver de banco ou o sistema de arquivos. |
| `config/` | Leitura de ambiente e parâmetros de execução. Sem regra de negócio. |
| `ingestion/` | Leitura de fontes e entrega de registros brutos ao restante do fluxo. |
| `transformations/` | Funções puras de transformação. Sem rede, disco ou relógio implícito. |
| `validation/` | Schema, nulos, duplicidade e regras de qualidade. Devolve resultado explícito. |
| `pipelines/` | Orquestra ingestão, transformação, validação e carga. Controla retry, log e parâmetros. |
| `infrastructure/` | Implementações de I/O: banco, arquivo, API, fila. |
| `utils/` | Funções genéricas, sem regra do domínio de dados. |
| `main.py` | Ponto de entrada. Monta a configuração e chama um pipeline. |

### Limites entre camadas

Dependências apontam para dentro. Uma camada de fora conhece o contrato da de dentro. A de dentro não conhece driver, caminho de arquivo nem variável de ambiente.

| Camada | Pode importar | Não importa |
| --- | --- | --- |
| `utils` | biblioteca padrão | `domain`, `pipelines`, `infrastructure`, `ingestion` |
| `domain` | biblioteca padrão e `utils` | `infrastructure`, `ingestion`, `pipelines`, `main` |
| `config` | biblioteca padrão | pipelines e drivers |
| `transformations`, `validation` | `domain`, `utils` | `infrastructure`, `ingestion`, `pipelines` |
| `infrastructure` | `domain`, `config`, `utils` | `pipelines`, `transformations` |
| `ingestion` | `domain`, `infrastructure`, `config`, `validation` | `pipelines`, `main` |
| `pipelines` | camadas acima, exceto `main` | — |
| `main` | `config`, `pipelines` | regra de negócio e SQL |

Contratos entre módulos são `Protocol` ou dataclasses do `domain`. A infraestrutura implementa o protocolo. O pipeline depende do protocolo, não da classe concreta do banco.

Regras de desenho:

- Uma função faz uma coisa. Se o nome precisa de "e", divida.
- Módulo acima de 300 linhas deve ser dividido por responsabilidade, salvo geração ou tabela de mapeamento justificada no review.
- Lógica repetida em dois módulos sobe para `domain`, `transformations` ou `utils`, conforme o tipo da regra.
- Imports circulares são defeito de fronteira. Extraia o contrato para `domain` em vez de importar os dois lados.
- `main.py` não filtra, não valida schema e não grava no destino.

Incorreto: negócio, I/O e orquestração no mesmo lugar.

```python
def main() -> None:
    rows = open("clientes.csv").read().splitlines()
    limpos = [r for r in rows if r and "email" in r]
    with open("saida.csv", "a", encoding="utf-8") as destino:
        destino.write("\n".join(limpos))
```

Correto: transformação pura, pipeline orquestra, `main` só dispara.

```python
def normalizar_clientes(linhas: list[str]) -> list[str]:
    """Mantém linhas não vazias que contenham e-mail."""
    return [linha for linha in linhas if linha and "email" in linha]


def main() -> None:
    executar_pipeline_clientes(carregar_config())
```

## 3. Padrões de código Python

O código segue PEP 8 (formato e nomes), PEP 257 (docstrings), PEP 484 (type hints) e PEP 585 (tipos genéricos nativos, como `list[str]` e `dict[str, int]`). Use a sintaxe moderna compatível com a versão fixada no pyenv. Em 3.10 ou superior, `X | None` é o padrão. `Optional[X]` fica para código que ainda precise de versões anteriores.

| Elemento | Convenção | Exemplo |
| --- | --- | --- |
| Módulo e pacote | `snake_case` | `validar_schema.py` |
| Função e variável | `snake_case` | `linhas_validas` |
| Classe e exceção | `PascalCase` | `ContratoCliente` |
| Constante de módulo | `MAIUSCULAS` | `LOTE_PADRAO` |
| Teste | `test_<comportamento>` | `test_rejeita_email_vazio` |

Obrigações:

- Funções e métodos públicos e internos têm type hints nos parâmetros e no retorno.
- Módulos, classes públicas e funções públicas têm docstring no estilo Google.
- Prefira funções curtas, com um nível de abstração só.
- Valores fixos de negócio viram constantes ou enums. Números mágicos soltos no meio da função são defeito.
- Use `dataclasses` para registros e resultados. Use `enum.Enum` para conjuntos fechados (status, camada medalhão, tipo de rejeição).
- Use `pathlib.Path` para caminhos. `os.path` e concatenação de strings ficam de fora.
- Use `logging` para diagnóstico da aplicação. `print` não é log.
- Configuração vem de variável de ambiente ou de arquivo de configuração sem segredo. Parâmetros de uma execução (data, lote, caminho de entrada) entram pelo pipeline, não como literal no meio da transformação.
- Abra arquivo, conexão e sessão com context manager.
- Exceção específica carrega contexto. `except Exception` que engole o erro é proibido. No bordo do pipeline, capturar `Exception` só é aceitável para registrar a falha e relançar, ou para convertê-la em erro de domínio.
- Código legível e direto prevalece sobre cadeia compacta difícil de testar.

Incorreto:

```python
import os

def gravar(df, caminho):
    try:
        print("gravando", os.environ["SENHA_BANCO"])
        open(caminho + "/out.csv", "w").write(str(df))
    except Exception:
        pass
```

Correto:

```python
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)
LOTE_PADRAO = 1_000


def gravar_csv(conteudo: str, destino: Path) -> None:
    """Grava o CSV completo no destino, substituindo o arquivo anterior."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8")
    logger.info("arquivo_gravado", extra={"destino": str(destino)})


def senha_banco() -> str:
    """Lê a senha do ambiente. Falha se a variável não existir."""
    try:
        return os.environ["SENHA_BANCO"]
    except KeyError as exc:
        raise RuntimeError("SENHA_BANCO não está definida") from exc
```

A senha é lida do ambiente e nunca entra na mensagem de log.

## 4. Ruff

O Ruff é a ferramenta oficial de lint, formatação e organização de imports. Black, Flake8, isort e Pylint não entram no fluxo do projeto.

O Ruff verifica estilo PEP 8, erros comuns, imports não usados, variáveis não usadas, complexidade e a ordem dos imports. O formatter aplica o layout. A correção automática roda antes da edição manual do que o Ruff já sabe consertar.

Comandos, a partir da raiz:

```bash
poetry run ruff check src tests --fix
poetry run ruff format src tests
poetry run ruff check src tests
poetry run ruff check --select I src tests
poetry run ruff format --check src tests
```

Os três últimos são a validação. `--fix` e `format` alteram arquivo. O check de formatter (`format --check`) é obrigatório no CI.

Configuração de referência no `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py312"
src = ["src", "tests"]
extend-exclude = [".venv", "site", "htmlcov"]

[tool.ruff.lint]
select = [
    "E", "W", "F", "I", "N", "UP", "B", "SIM",
    "C4", "PIE", "RET", "RUF", "ARG", "C90",
    "BLE", "S",
    "D100", "D101", "D102", "D103",
]
fixable = ["ALL"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.isort]
known-first-party = ["projeto"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D100", "D101", "D102", "D103", "S101"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

`target-version` acompanha o `.python-version`. `S101` fica ignorado só em teste, porque o pytest usa `assert`. Fora de `tests/`, suprimir diagnóstico exige `# noqa: CODIGO` com o motivo técnico na mesma linha. Prefira corrigir o código.

O Ruff roda antes de cada commit e no CI. Commit com lint ou formatação pendente não entra na branch principal.

## 5. Testes com pytest

O pytest é o framework oficial. pytest-cov mede a cobertura do pacote `projeto`, que corresponde a `src/projeto`. A cobertura dos próprios testes não entra no cálculo. O mínimo aceito é **50%**. Esse número é o piso inicial. Conforme o projeto amadurece, suba `fail_under`. Reduzir o piso, excluir módulo de produção ou marcar linha como coberta para o CI passar é proibido.

Testes unitários são obrigatórios para funções e módulos que contêm regra, transformação ou validação.

Cada unidade relevante cobre:

- caminho de sucesso;
- entrada inválida;
- limite (vazio, nulo, duplicado, zero, coleção de um elemento);
- exceção esperada.

Organize `tests/unit/` como espelho de `src/projeto`. Arquivos se chamam `test_*.py`. Funções se chamam `test_<comportamento>`. Fixture compartilhada fica em `tests/conftest.py` e só prepara cenário. Testes de integração ficam em `tests/integration/` e podem usar serviço externo. Testes unitários não usam rede, banco real, API nem relógio do sistema. Dependência externa é substituída por fake ou mock.

Os testes são determinísticos: mesma entrada, mesmo resultado, sem depender de ordem, fuso horário da máquina ou arquivo fora de `tests/`.

Comandos:

```bash
poetry run pytest
poetry run pytest --cov=projeto --cov-report=term-missing
poetry run pytest --cov=projeto --cov-report=html
poetry run pytest --cov=projeto --cov-fail-under=50
```

O comando que libera a entrega é o último. O relatório HTML é apoio local e o diretório `htmlcov/` não é versionado.

Configuração:

```toml
[tool.pytest.ini_options]
testpaths = ["tests/unit"]
pythonpath = ["src"]
addopts = "--cov=projeto --cov-report=term-missing --cov-fail-under=50"
markers = [
    "integration: depende de serviço externo e não entra no gate padrão",
]

[tool.coverage.run]
source = ["projeto"]
branch = true

[tool.coverage.report]
show_missing = true
fail_under = 50
```

`testpaths = ["tests/unit"]` faz `poetry run pytest` executar só a suíte isolada. Integração roda de forma explícita:

```bash
poetry run pytest tests/integration -m integration --cov-fail-under=0
```

Exemplo de teste que exercita regra, não um assert vazio:

```python
import pytest

from projeto.transformations.clientes import normalizar_email


def test_normaliza_email_com_espaco_e_maiuscula() -> None:
    assert normalizar_email(" Ana@Empresa.com ") == "ana@empresa.com"


def test_rejeita_email_vazio() -> None:
    with pytest.raises(ValueError):
        normalizar_email("   ")
```

## 6. Documentação com MkDocs Material

A documentação técnica vive no repositório, em Markdown, gerada pelo MkDocs com o tema Material. MkDocs Material é dependência do grupo `dev`.

Páginas mínimas:

| Arquivo | Conteúdo |
| --- | --- |
| `docs/index.md` | O que o projeto faz e por onde começar |
| `docs/architecture.md` | Camadas, fluxo dos dados, fontes, destinos e decisões |
| `docs/development.md` | Instalação, execução, testes, lint e troubleshooting |

Inclua páginas próprias quando o assunto existir de fato:

- módulos e responsabilidades;
- pipelines e parâmetros de execução;
- fontes e destinos;
- transformações e regras de negócio;
- contratos de dados e qualidade;
- como rodar os testes;
- troubleshooting;
- ADRs em `docs/adr/` para decisões que custam caro reverter.

A documentação descreve o comportamento atual, traz exemplos de execução e usa diagrama quando o fluxo entre camadas ou entre Bronze, Silver e Gold não cabe em um parágrafo. Link quebrado e página órfã falham o build estrito.

`mkdocs.yml` inicial:

```yaml
site_name: Projeto
docs_dir: docs
theme:
  name: material
  language: pt
  features:
    - navigation.instant
    - navigation.tracking
    - navigation.sections
    - search.suggest
    - search.highlight
    - content.code.copy
nav:
  - Início: index.md
  - Arquitetura: architecture.md
  - Desenvolvimento: development.md
markdown_extensions:
  - admonition
  - tables
  - toc:
      permalink: true
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.highlight
```

Comandos:

```bash
poetry run mkdocs serve
poetry run mkdocs build --strict
```

`mkdocs serve` é a conferência local. `mkdocs build --strict` é a validação de CI. O diretório `site/` não é versionado. O `README.md` repete pré-requisitos, instalação e o comando de execução, e aponta para `docs/`.

## 7. Pipelines de dados

Separe o fluxo em quatro momentos: ingerir, transformar, validar e disponibilizar. Cada momento tem módulo próprio. O pipeline chama os quatro. Ele não reimplementa a regra.

- Transformações são funções puras sempre que a regra permitir: a saída depende só dos argumentos.
- Uma reexecução com os mesmos parâmetros não duplica registro nem altera resultado já publicado. Grave de forma substitutiva na partição afetada, ou faça upsert pela chave de negócio. Evite `append` cego.
- Dados inválidos têm destino explícito: rejeição com motivo, contagem e identificador do registro. Eles não desaparecem num `except` nem interrompem o lote inteiro sem registro do que foi rejeitado.
- Todo conjunto que muda de camada passa por validação de schema (colunas, tipos e obrigatoriedade).
- Duplicidade é decidida por chave de negócio documentada. A regra fica em `validation` ou `transformations`, com teste.
- Nulos em campo obrigatório reprovam o registro. Nulos em campo opcional permanecem nulos. Não converta nulo em zero ou string vazia sem regra de negócio escrita.
- Log estruturado em cada etapa: pipeline, partição ou data de referência, volume lido, volume aceito, volume rejeitado e duração. Use `extra` no logger. Não use texto solto como único formato.
- Falha de I/O pode ter retry com limite e intervalo, na infraestrutura ou no bordo do pipeline. Retry não envolve transformação que já publicou efeito parcial sem controle de idempotência.
- Parâmetros de execução (data, ambiente, caminho, nome da fonte) vêm de configuração. O código não carrega a data de um fechamento específico.
- Código e dado ficam separados. Extrações, dumps e bases reais não entram no Git. Fixture sintética e pequena pode viver em `tests/`.
- Credencial de fonte e destino vem do ambiente ou de um cofre. A conexão usa o driver com parâmetro vinculado. SQL é montado com placeholder, nunca com f-string de valor externo.
- A mesma transformação, com a mesma entrada, produz a mesma saída em outra máquina. Relógio e aleatoriedade entram como argumento quando influenciam o resultado.
- Leia e grave só as colunas e partições necessárias. Não carregue um histórico inteiro para produzir um recorte diário.
- Processamento distribuído entra quando o volume, o tempo de execução ou a plataforma do time justificam. Um lote que cabe em memória local permanece em função simples e testável.

Arquitetura medalhão, quando o fluxo tem mais de um estágio de qualidade:

| Camada | Conteúdo |
| --- | --- |
| Bronze | Dado bruto, como chegou da fonte, com data de ingestão |
| Silver | Dado conformado ao contrato: tipo, chave e deduplicação |
| Gold | Dado para consumo, na granularidade da regra de negócio |

Contrato de dados: nome da coluna, tipo, nulabilidade, chave e regra de qualidade. O contrato fica em `domain` ou `validation` e é o que o teste de schema garante. Cada execução deixa rastro suficiente para auditar o que entrou, o que foi rejeitado e o que foi publicado.

Incorreto: append repetido e SQL montado com entrada externa.

```python
def carregar(conn, tabela, data_texto):
    conn.execute(f"INSERT INTO {tabela} SELECT * FROM origem WHERE dia = '{data_texto}'")
```

Correto: parâmetro vinculado e escrita idempotente da partição.

```python
def publicar_particao(conn, dia: str, linhas: list[tuple]) -> None:
    """Substitui a partição do dia e insere as linhas aceitas."""
    conn.execute("DELETE FROM destino WHERE dia = %s", (dia,))
    conn.executemany(
        "INSERT INTO destino (dia, cliente_id, valor) VALUES (%s, %s, %s)",
        linhas,
    )
```

## 8. Segurança e qualidade

- Segredos ficam em variável de ambiente ou cofre. O repositório leva `.env.example` só com os nomes das variáveis, sem valor.
- `.env`, chaves, JSON de credencial e connection string com senha estão no `.gitignore` e não aparecem no histórico.
- Log, exceção e mensagem de erro não incluem senha, token, chave ou connection string completa.
- Entrada externa (arquivo, API, parâmetro de CLI, coluna de origem) é validada antes de virar SQL, caminho de escrita ou chamada de sistema.
- Consulta SQL usa parâmetro do driver. Nome de tabela ou coluna, se precisar ser dinâmico, vem de uma lista fechada do próprio código.
- Conexão com fonte e destino usa o canal seguro exigido pelo ambiente (TLS quando o serviço oferece) e a credencial de menor privilégio que ainda cumpre a tarefa.
- Dependências novas passam por `poetry add`. No review, olhe o diff de `pyproject.toml` e de `poetry.lock`.
- Quando o projeto acessa rede, dado sensível ou segue para produção, rode análise das dependências no CI. Ruff com o conjunto `S` cobre defeitos comuns no código. Ele não substitui a guarda dos segredos nem a revisão do lock.

`.gitignore` mínimo:

```gitignore
.venv/
.env
__pycache__/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
site/
dist/
*.egg-info/
data/raw/
data/bronze/
data/silver/
data/gold/
```

## 9. CI/CD

Antes de merge ou deploy, o pipeline de integração executa, nesta ordem:

1. Conferência da versão do Python a partir de `.python-version`.
2. `poetry install`.
3. `poetry run ruff check src tests`.
4. `poetry run ruff format --check src tests`.
5. `poetry run ruff check --select I src tests`.
6. `poetry run pytest --cov=projeto --cov-report=term-missing --cov-fail-under=50`.
7. `poetry run mkdocs build --strict`.
8. Análise de segurança das dependências, quando o projeto acessa rede, dado sensível ou vai a produção.

O exemplo abaixo é uma sugestão para GitHub Actions. Outra plataforma deve executar os mesmos comandos.

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version-file: .python-version

      - name: Instalar Poetry
        run: pipx install poetry

      - name: Instalar dependências
        run: poetry install

      - name: Ruff lint
        run: poetry run ruff check src tests

      - name: Ruff format
        run: poetry run ruff format --check src tests

      - name: Ruff imports
        run: poetry run ruff check --select I src tests

      - name: Testes e cobertura
        run: poetry run pytest --cov=projeto --cov-report=term-missing --cov-fail-under=50

      - name: Documentação
        run: poetry run mkdocs build --strict
```

## 10. Git

- Commits pequenos, cada um com um propósito verificável.
- Mensagens no padrão Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- Branches curtas e nomeadas pelo trabalho, por exemplo `feat/validar-schema-cliente`.
- Pull request descreve a mudança, o risco de dados e como foi validada.
- Review confere arquitetura, testes, cobertura, segredos e o diff do lock.
- Código sem lint ou sem teste correspondente não é commitado na branch principal.
- Não se versiona virtualenv, cache, `.env`, credencial, dado real nem o site gerado do MkDocs.
- Mudança em `pyproject.toml` vem acompanhada de `poetry.lock` atualizado.

## 11. Fluxo esperado da IA

Ao implementar ou modificar um projeto com esta skill:

1. Leia a estrutura real do repositório antes de criar arquivo ou mover código.
2. Identifique a versão em `.python-version`, em `pyenv version` e em `poetry env info`.
3. Respeite as camadas já existentes. Encaixe código novo na camada dona daquela responsabilidade.
4. Altere só o que a tarefa pede.
5. Implemente em módulos coesos, com contrato explícito entre eles.
6. Gerencie pacotes somente com Poetry.
7. Execute o Ruff de lint, formatação e imports, e corrija o que falhar.
8. Crie ou atualize testes unitários dos cenários de sucesso, erro, limite e exceção.
9. Mantenha a cobertura de `projeto` em pelo menos 50%, sem baixar o limiar.
10. Atualize a documentação MkDocs quando a arquitetura, a execução ou o contrato de dados mudar.
11. Rode os comandos de validação nesta sessão, antes de declarar a tarefa pronta.
12. Informe falha, limite e pendência de forma direta.
13. Não afirme que lint, teste, cobertura ou documentação passaram sem ter executado o comando.

## 12. Checklists

### Desenvolvimento

- [ ] `.python-version` e `requires-python` descrevem a mesma linha de versão
- [ ] `poetry env info` aponta para `.venv` e para o Python do pyenv
- [ ] Dependência nova entrou por `poetry add` ou `poetry add --group dev`
- [ ] `poetry.lock` está atualizado
- [ ] Código novo está na camada correta e `main.py` só dispara o pipeline
- [ ] Transformação pura tem teste sem rede
- [ ] Segredo não aparece em código, teste, log ou documentação
- [ ] `poetry run ruff check src tests` e `poetry run ruff format --check src tests` passam
- [ ] `poetry run pytest --cov=projeto --cov-fail-under=50` passa
- [ ] Docs afetadas foram atualizadas

### Revisão de código

- [ ] A mudança respeita os limites de import entre camadas
- [ ] Não há regra de negócio nova em `main.py` ou na infraestrutura
- [ ] Funções novas são objetivas e a complexidade permanece dentro do limite do Ruff
- [ ] Não há `except` genérico engolindo erro, SQL concatenado nem `print` de aplicação
- [ ] Testes cobrem sucesso, falha, limite e exceção do comportamento alterado
- [ ] A cobertura não foi reduzida por exclusão artificial
- [ ] `pyproject.toml` e `poetry.lock` batem, e não entrou pacote desnecessário
- [ ] Não há credencial, dado real ou `.env` no diff
- [ ] A documentação continua descrevendo o comportamento mergeado

### Entrega

- [ ] CI executou Ruff (lint, formato e imports), pytest com piso de 50% e `mkdocs build --strict`
- [ ] Pipeline é idempotente na partição ou na chave que a mudança afeta
- [ ] Contrato de dados e rejeições estão descritos
- [ ] README e `docs/development.md` permitem instalar e executar do zero
- [ ] Pendências conhecidas estão escritas no pull request

## 13. Critérios de aceite

Uma entrega está aceita quando:

1. A versão local do Python está no pyenv e em `.python-version`.
2. As dependências estão no Poetry, instaladas na virtualenv do projeto, com `poetry.lock` versionado.
3. A estrutura segue o layout `src/` e as regras de dependência entre camadas.
4. `poetry run ruff check src tests` termina sem erro.
5. `poetry run ruff format --check src tests` termina sem erro.
6. `poetry run ruff check --select I src tests` termina sem erro.
7. `poetry run pytest --cov=projeto --cov-report=term-missing --cov-fail-under=50` passa, com cobertura medida sobre o pacote da aplicação.
8. A documentação existe no MkDocs Material e `poetry run mkdocs build --strict` passa.
9. Não há segredo, dado real nem dependência global compondo a solução.
10. O resultado desses comandos foi obtido por execução real e informado a quem pediu a mudança.

## Configuração consolidada do `pyproject.toml`

Ponto de partida. Ajuste nome, descrição e `target-version` ao repositório.

```toml
[project]
name = "projeto"
version = "0.1.0"
description = ""
readme = "README.md"
requires-python = ">=3.12,<3.13"
dependencies = []

[dependency-groups]
dev = [
    "ruff",
    "pytest",
    "pytest-cov",
    "mkdocs-material",
]

[tool.poetry]
packages = [{ include = "projeto", from = "src" }]

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.ruff]
line-length = 88
target-version = "py312"
src = ["src", "tests"]
extend-exclude = [".venv", "site", "htmlcov"]

[tool.ruff.lint]
select = [
    "E", "W", "F", "I", "N", "UP", "B", "SIM",
    "C4", "PIE", "RET", "RUF", "ARG", "C90",
    "BLE", "S",
    "D100", "D101", "D102", "D103",
]
fixable = ["ALL"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.isort]
known-first-party = ["projeto"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D100", "D101", "D102", "D103", "S101"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.pytest.ini_options]
testpaths = ["tests/unit"]
pythonpath = ["src"]
addopts = "--cov=projeto --cov-report=term-missing --cov-fail-under=50"
markers = [
    "integration: depende de serviço externo e não entra no gate padrão",
]

[tool.coverage.run]
source = ["projeto"]
branch = true

[tool.coverage.report]
show_missing = true
fail_under = 50
```
